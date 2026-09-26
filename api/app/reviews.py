"""The Daily Review (#9): opening Round 1 on the Learner's first use of the day, reading the
day's Review Rounds, and answering their Questions. The timing and picking rules are the plain
functions in `app/review.py`; this module stores what they decide.

- **The first use of the day** (`start_day`) is any signed-in request by an onboarded Learner:
  the `deps.open_daily_review` dependency runs it on every route of the main router, before the
  route itself. The first one on a calendar day (in the Learner's time zone) records a
  `ReviewDay` and opens Round 1, if a Daily Review is owed. Later requests that day find the
  `ReviewDay` and open nothing. A Learner with no Completed Lesson at that moment owes nothing
  that day, even if they complete a Lesson later the same day.
- **Round 1** asks up to ten Questions (`review.pick_round_questions`): the Learner's Missed
  Questions first (`quizzes.missed_question_ids`, first missed first), then Questions of their
  Completed Lessons at random. Both come from the Stack's current Syllabus version, which the
  round is pinned to, so a round in progress when a new version is imported finishes on the
  old one (#13).
- **Answering** is one Question at a time (`answer_question`), marked by `marking.mark` like a
  Lesson Quiz: a written answer is graded against its Model Answer, and if grading fails
  nothing is recorded and the Learner answers again. Every answer is an `Answer` with
  `context='review_round'`, so a wrong one is a Missed Question too. Each Question is answered
  once; the round is finished when the last one is.
- **Pending**: two hours after opening, an unfinished round is a Pending Review Round, and the
  Unlocked Lesson is locked until it's finished (`progress.pending_review_round`, which the
  lock states and the Lesson Quiz guard read). Only rounds of the Learner's current day count:
  an unfinished round from an earlier day is dropped (answering it is refused with
  `RoundDropped`) and blocks nothing.

Not built yet: Rounds 2 and 3 and carry-over (#10: open them in `start_day`'s place on each
request, and lead with the dropped rounds' unanswered Questions), leaving the rotation (#10:
filter `missed_ids` by correct answers on three different days), the Streak (#11: read
`ReviewDay`s and their rounds in day order), and Updated Lessons' new Questions (#13: put
them after the Missed Questions in `_round_1_questions`).
"""

import random
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import progress, quizzes, review
from app.grading import Grader
from app.marking import AnswerTooLong, GradingFailed, NotAChoice, mark
from app.models import (
    Answer,
    LearnerStack,
    Lesson,
    Question,
    ReviewDay,
    ReviewRound,
    Stack,
    Syllabus,
)
from app.review import RoundState

REVIEW_ROUND = "review_round"
"""`Answer.context` for an answer given in a Review Round."""


class RoundNotFound(Exception):
    """No such Review Round for this Learner and Stack."""


class RoundFinished(Exception):
    """Every Question of the round is already answered."""


class RoundDropped(Exception):
    """The round belongs to an earlier day: it was dropped at the end of that day."""


class QuestionAnswered(Exception):
    """The Question was already answered in this round."""


class QuestionNotInRound(Exception):
    def __init__(self, question_id: str) -> None:
        super().__init__(question_id)
        self.question_id = question_id


@dataclass(frozen=True)
class RoundView:
    """A Review Round as it stands at `now`."""

    round: ReviewRound
    state: RoundState
    questions: list[Question]
    """From the round's pinned version, in the order they are asked. They include the correct
    answers: never send those for a Question not yet answered."""
    answers: dict[str, Answer]
    """The answers given so far, by Question ID."""

    @property
    def remaining(self) -> list[Question]:
        """The Questions still to answer, in the order they are asked."""
        return [q for q in self.questions if q.id not in self.answers]

    @property
    def answered(self) -> list[tuple[Question, Answer]]:
        """The Questions answered so far, with their answers, in the order they are asked."""
        return [(q, self.answers[q.id]) for q in self.questions if q.id in self.answers]


@dataclass(frozen=True)
class DailyReview:
    """The Learner's Daily Review for one day: its Review Rounds so far, in order. Empty on a
    day with nothing owed."""

    day: date
    rounds: list[RoundView]

    @property
    def current(self) -> RoundView | None:
        """The round waiting to be answered, if any."""
        return next((r for r in reversed(self.rounds) if r.state != "finished"), None)


@dataclass(frozen=True)
class AnswerResult:
    round: RoundView
    """The round after this answer."""
    question: Question
    response: str | None
    correct: bool
    feedback: str | None
    """The grader's one line, for a graded written answer."""


def start_day(
    session: Session, record: LearnerStack, time_zone: str, now: datetime, rng: random.Random
) -> None:
    """Record the Learner's use of the app at `now`. The first use of a calendar day (in
    `time_zone`) opens Round 1 of that day's Daily Review, if one is owed; later uses that day
    change nothing. Safe to call on every request, concurrently too."""
    day = review.review_day(time_zone, now)
    key = (record.learner_id, record.stack_id, day)
    if session.get(ReviewDay, key) is not None:
        return
    first_use = session.execute(
        insert(ReviewDay)
        .values(learner_id=record.learner_id, stack_id=record.stack_id, day=day, first_used_at=now)
        .on_conflict_do_nothing()
        .returning(ReviewDay.day)
    ).first()
    if first_use is None:  # another request got there first
        return
    picked = _round_1_questions(session, record, rng)
    if picked is not None:
        version, question_ids = picked
        session.add(
            ReviewRound(
                id=uuid.uuid4(),
                learner_id=record.learner_id,
                stack_id=record.stack_id,
                day=day,
                number=1,
                syllabus_version=version,
                question_ids=question_ids,
                opened_at=now,
            )
        )
    session.commit()


def daily_review(
    session: Session, learner_id: int, stack_id: str, time_zone: str, now: datetime
) -> DailyReview:
    """The Learner's Daily Review for the day it is at `now` in `time_zone`."""
    day = review.review_day(time_zone, now)
    rounds = session.scalars(
        select(ReviewRound)
        .where(
            ReviewRound.learner_id == learner_id,
            ReviewRound.stack_id == stack_id,
            ReviewRound.day == day,
        )
        .order_by(ReviewRound.number)
    ).all()
    return DailyReview(day, [_view(session, r, now) for r in rounds])


def answer_question(
    session: Session,
    record: LearnerStack,
    time_zone: str,
    round_id: uuid.UUID,
    question_id: str,
    response: str | None,
    grader: Grader,
    now: datetime,
) -> AnswerResult:
    """Mark and record the answer to one Question of a Review Round of today: a choice ID or a
    written answer. None (or a blank written answer) is unanswered, so wrong. The last answer
    finishes the round.

    Raises RoundNotFound, RoundFinished, RoundDropped, QuestionNotInRound, QuestionAnswered,
    NotAChoice, AnswerTooLong or GradingFailed; nothing is recorded then. A written answer is
    graded while the round's row is locked, so a double submission can't grade twice.
    """
    round_ = session.scalar(
        select(ReviewRound)
        .where(
            ReviewRound.id == round_id,
            ReviewRound.learner_id == record.learner_id,
            ReviewRound.stack_id == record.stack_id,
        )
        .with_for_update()
    )
    if round_ is None:
        raise RoundNotFound(round_id)
    if round_.finished_at is not None:
        raise RoundFinished(round_id)
    if round_.day != review.review_day(time_zone, now):
        raise RoundDropped(round_id)
    if question_id not in round_.question_ids:
        raise QuestionNotInRound(question_id)
    before = _view(session, round_, now)
    if question_id in before.answers:
        raise QuestionAnswered(question_id)

    question = next(q for q in before.questions if q.id == question_id)
    try:
        marked = mark(question, response, grader)
    except (NotAChoice, AnswerTooLong, GradingFailed):
        session.rollback()  # releases the lock; nothing was written
        raise
    session.add(
        Answer(
            learner_id=record.learner_id,
            stack_id=record.stack_id,
            question_id=question.id,
            syllabus_version=round_.syllabus_version,
            context=REVIEW_ROUND,
            review_round_id=round_.id,
            response=response,
            correct=marked.correct,
            feedback=marked.feedback,
            answered_at=now,
        )
    )
    if len(before.remaining) == 1:
        round_.finished_at = now
    session.commit()
    return AnswerResult(
        _view(session, round_, now), question, response, marked.correct, marked.feedback
    )


def _round_1_questions(
    session: Session, record: LearnerStack, rng: random.Random
) -> tuple[str, list[str]] | None:
    """The current Syllabus version and the Questions for Round 1, or None when no Daily Review
    is owed: no Completed Lesson, or nothing to ask."""
    completed = progress.completed_lesson_ids(session, record.learner_id, record.stack_id)
    syllabus = session.scalar(
        select(Syllabus)
        .join(Stack, Stack.current_syllabus_pk == Syllabus.pk)
        .where(Stack.id == record.stack_id)
    )
    if not completed or syllabus is None:
        return None
    bank = session.execute(
        select(Question.id, Lesson.id)
        .join(Lesson, Lesson.pk == Question.lesson_pk)
        .where(Question.syllabus_pk == syllabus.pk)
        .order_by(Lesson.position, Question.position)
    ).all()
    in_version = {question_id for question_id, _ in bank}
    missed = [
        q
        for q in quizzes.missed_question_ids(session, record.learner_id, record.stack_id)
        if q in in_version  # a Question a later version removed has left the rotation
    ]
    from_completed = [question_id for question_id, lesson_id in bank if lesson_id in completed]
    picked = review.pick_round_questions(missed, from_completed, rng)
    return (syllabus.version, picked) if picked else None


def _view(session: Session, round_: ReviewRound, now: datetime) -> RoundView:
    answers = session.scalars(select(Answer).where(Answer.review_round_id == round_.id)).all()
    return RoundView(
        round_,
        review.round_state(round_.opened_at, round_.finished_at, now),
        _version_questions(session, round_.stack_id, round_.syllabus_version, round_.question_ids),
        {a.question_id: a for a in answers},
    )


def _version_questions(
    session: Session, stack_id: str, version: str, question_ids: Sequence[str]
) -> list[Question]:
    """Questions of one Syllabus version, in the order of `question_ids`."""
    rows = session.scalars(
        select(Question)
        .join(Syllabus, Syllabus.pk == Question.syllabus_pk)
        .where(
            Syllabus.stack_id == stack_id,
            Syllabus.version == version,
            Question.id.in_(question_ids),
        )
    ).all()
    by_id = {q.id: q for q in rows}
    return [by_id[qid] for qid in question_ids]
