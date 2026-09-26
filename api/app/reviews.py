"""The Daily Review (#9, #10): opening Review Rounds, reading the day's rounds, and answering
their Questions. The timing and picking rules are the plain functions in `app/review.py`; this
module stores what they decide.

- **Opening rounds** (`start_day`) happens on any signed-in request by an onboarded Learner:
  the `deps.open_daily_review` dependency runs it on every route of the main router, before the
  route itself.
  - The first request on a calendar day (in the Learner's time zone) records a `ReviewDay` and
    opens Round 1, if a Daily Review is owed. A Learner with no Completed Lesson at that moment
    owes nothing that day, even if they complete a Lesson later the same day.
  - Every later request opens the next round once its time has come
    (`review.next_round_opens_at`: four hours after the previous round is finished, at most
    three rounds, never past the day's end). The round's `opened_at` is that time, not the
    request's, so a Learner who comes back late finds it already pending.
- **A round's Questions** (`_round_questions`, up to ten, `review.pick_round_questions`) come
  from these sources, in order:
  1. the unanswered Questions of the rounds dropped on the Learner's previous day with rounds
     (`_carried_over`), whichever day that was;
  2. Missed Questions still in the rotation, first missed first (`_missed_in_rotation`): a
     Missed Question leaves it once answered correctly on three different days since it was
     last missed;
  3. Updated Lessons' new Questions (#13's slot, empty for now);
  4. Questions of Completed Lessons at random.
  Questions already asked that day are left out unless a round would be short (then Completed
  Lessons' Questions repeat). All come from the Stack's current Syllabus version, which the
  round is pinned to, so a round in progress when a new version is imported finishes on the
  old one (#13).
- **Answering** is one Question at a time (`answer_question`), marked by `marking.mark` like a
  Lesson Quiz: a written answer is graded against its Model Answer, and if grading fails
  nothing is recorded and the Learner answers again. Every answer is an `Answer` with
  `context='review_round'`, so a wrong one is a Missed Question too. Each Question is answered
  once; the round is finished when the last one is.
- **Pending**: two hours after opening, an unfinished round is a Pending Review Round, and the
  Unlocked Lesson is locked until it's finished (`progress.pending_review_round`, which the
  lock states and the Lesson Quiz guard read). A round opens only once the one before it is
  finished, so at most one round is pending. Only rounds of the Learner's current day count:
  an unfinished round from an earlier day is dropped (answering it is refused with
  `RoundDropped`) and blocks nothing.

Not built yet: the Streak (#11: read `ReviewDay`s and their rounds in day order; a day's rounds
were all finished when each is finished and `review.next_round_opens_at` of the day is None),
and Updated Lessons' new Questions (#13: fill `updated` in `_round_questions`).
"""

import random
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
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
    time_zone: str
    """The Learner's, which `day` is in."""
    rounds: list[RoundView]
    next_round_at: datetime | None
    """When the day's next round opens, if one is still to open today."""

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
    """Record the Learner's use of the app at `now`, and open any Review Round due by then.

    The first use of a calendar day (in `time_zone`) opens Round 1 of that day's Daily Review,
    if one is owed. Later uses open Round 2 or 3 once due, with `opened_at` the time it became
    due. Safe to call on every request, concurrently too: a round is opened once."""
    day = review.review_day(time_zone, now)
    key = (record.learner_id, record.stack_id, day)
    if session.get(ReviewDay, key) is None:
        first_use = session.execute(
            insert(ReviewDay)
            .values(
                learner_id=record.learner_id, stack_id=record.stack_id, day=day, first_used_at=now
            )
            .on_conflict_do_nothing()
            .returning(ReviewDay.day)
        ).first()
        if first_use is None:  # another request got there first
            return
        _open_round(session, record, time_zone, day, 1, now, rng)
        session.commit()
        return
    rounds = _rounds_of(session, record.learner_id, record.stack_id, day)
    opens_at = review.next_round_opens_at([r.finished_at for r in rounds], time_zone, day)
    if opens_at is not None and now >= opens_at:
        _open_round(session, record, time_zone, day, len(rounds) + 1, opens_at, rng)
        session.commit()


def _open_round(
    session: Session,
    record: LearnerStack,
    time_zone: str,
    day: date,
    number: int,
    opened_at: datetime,
    rng: random.Random,
) -> None:
    """Open round `number` of `day`, unless there is nothing to ask or another request already
    opened it."""
    picked = _round_questions(session, record, time_zone, day, rng)
    if picked is None:
        return
    version, question_ids = picked
    session.execute(
        insert(ReviewRound)
        .values(
            id=uuid.uuid4(),
            learner_id=record.learner_id,
            stack_id=record.stack_id,
            day=day,
            number=number,
            syllabus_version=version,
            question_ids=question_ids,
            opened_at=opened_at,
        )
        .on_conflict_do_nothing(index_elements=["learner_id", "stack_id", "day", "number"])
    )


def _rounds_of(session: Session, learner_id: int, stack_id: str, day: date) -> list[ReviewRound]:
    """The Learner's Review Rounds of `day`, in order."""
    return list(
        session.scalars(
            select(ReviewRound)
            .where(
                ReviewRound.learner_id == learner_id,
                ReviewRound.stack_id == stack_id,
                ReviewRound.day == day,
            )
            .order_by(ReviewRound.number)
        )
    )


def daily_review(
    session: Session, learner_id: int, stack_id: str, time_zone: str, now: datetime
) -> DailyReview:
    """The Learner's Daily Review for the day it is at `now` in `time_zone`."""
    day = review.review_day(time_zone, now)
    rounds = _rounds_of(session, learner_id, stack_id, day)
    opens_at = review.next_round_opens_at([r.finished_at for r in rounds], time_zone, day)
    return DailyReview(
        day,
        time_zone,
        [_view(session, r, now) for r in rounds],
        # Past its time but not opened: there was nothing to ask, so it never opens.
        opens_at if opens_at is not None and opens_at > now else None,
    )


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


def _round_questions(
    session: Session, record: LearnerStack, time_zone: str, day: date, rng: random.Random
) -> tuple[str, list[str]] | None:
    """The current Syllabus version and the Questions for the next round of `day`, or None when
    no Daily Review is owed: no Completed Lesson, or nothing to ask. The sources, in order, are
    `review.RoundSources`; each keeps only Questions of the current version (a Question a later
    version removed has left the rotation)."""
    learner_id, stack_id = record.learner_id, record.stack_id
    completed = progress.completed_lesson_ids(session, learner_id, stack_id)
    syllabus = session.scalar(
        select(Syllabus)
        .join(Stack, Stack.current_syllabus_pk == Syllabus.pk)
        .where(Stack.id == stack_id)
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

    def current(question_ids: Sequence[str]) -> list[str]:
        return [q for q in question_ids if q in in_version]

    sources = review.RoundSources(
        carried_over=current(_carried_over(session, learner_id, stack_id, day)),
        missed=current(_missed_in_rotation(session, learner_id, stack_id, time_zone)),
        updated=[],  # #13: the new Questions of the Learner's Updated Lessons go here
        completed=[question_id for question_id, lesson_id in bank if lesson_id in completed],
        asked_today={
            q for r in _rounds_of(session, learner_id, stack_id, day) for q in r.question_ids
        },
    )
    picked = review.pick_round_questions(sources, rng)
    return (syllabus.version, picked) if picked else None


def _carried_over(session: Session, learner_id: int, stack_id: str, day: date) -> list[str]:
    """The unanswered Questions of the rounds left unfinished (so dropped) on the Learner's
    last day with rounds before `day`, in the order they were asked. That day need not be
    yesterday: they wait for the Learner's next day with rounds."""
    previous = session.scalar(
        select(func.max(ReviewRound.day)).where(
            ReviewRound.learner_id == learner_id,
            ReviewRound.stack_id == stack_id,
            ReviewRound.day < day,
        )
    )
    if previous is None:
        return []
    dropped = [
        r for r in _rounds_of(session, learner_id, stack_id, previous) if r.finished_at is None
    ]
    answers = session.execute(
        select(Answer.review_round_id, Answer.question_id).where(
            Answer.review_round_id.in_([r.id for r in dropped])
        )
    ).all()
    return review.carried_over(
        (r.question_ids, {q for round_id, q in answers if round_id == r.id}) for r in dropped
    )


def _missed_in_rotation(
    session: Session, learner_id: int, stack_id: str, time_zone: str
) -> list[str]:
    """The Learner's Missed Questions still in the rotation (`review.in_rotation`), first
    missed first. Correct answers in any context count, on days in `time_zone`."""
    correct: dict[str, list[datetime]] = {}
    for question_id, answered_at in session.execute(
        select(Answer.question_id, Answer.answered_at).where(
            Answer.learner_id == learner_id,
            Answer.stack_id == stack_id,
            Answer.correct.is_(True),
        )
    ):
        correct.setdefault(question_id, []).append(answered_at)
    return [
        m.question_id
        for m in quizzes.missed_questions(session, learner_id, stack_id)
        if review.in_rotation(m.last_missed_at, correct.get(m.question_id, []), time_zone)
    ]


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
