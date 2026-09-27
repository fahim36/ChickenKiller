"""Daily Challenges, as imported (#16), played (#17) and archived (#19).

**The Admin's view** (`challenges_ahead`): how far ahead each Stack's Challenges are written. It
only counts Days.

**Playing** (`todays_challenge`, `challenge_state`, `answer`). All Days are UTC Days (ADR-0005):

- Only a released Challenge (`is_frozen`: its Day has begun) is ever read for a Learner. An
  Upcoming Challenge's Questions are never sent, and answering one is refused like an unknown
  Challenge (`ChallengeNotFound`).
- Today's Challenge on a Stack is the one dated today. Every released one is in the Stack's
  Archive (#19), and a Learner can answer any of them: today's, from home or the Archive alike,
  or a past one. A play is on its Day only if it is finished on the Challenge's own Day, so an
  Archive play of a past Challenge never counts toward a Streak, though it is scored and its
  misses are Missed Questions like any first play.
- **Only the first answer to each Question is scored.** It is an `Answer` with
  `context='daily_challenge'`, linked to the Learner's `ChallengePlay` (created by their first
  answer), so a wrong one is a Missed Question and every one counts as seen. Nothing else from a
  Challenge is ever stored: a later answer to the same Question, and every answer of a replay,
  is marked and shown with its Explanation and Sources, and changes no score, Streak or Missed
  Question, nor Review's count of correct Days.
- A written first answer whose grading fails (#7) is recorded with `correct` null: that
  Question is **ungraded** for good and earns no point. The Learner can resubmit for feedback,
  which, like any later answer, counts for nothing. A later answer whose grading fails raises
  `GradingFailed`: nothing was counted, and the Learner can send it again.
- A Retired Question can't be answered (`QuestionRetired`), and the score counts only the
  Questions that can be. Once each of those has its first answer the play is finished: its
  score, its UTC Day and whether that was the Challenge's own Day are set once, for the Streak
  (#18) and the Result Card. A Retired Question is shown with its reason and its replacement, if
  it has one, linked to the first released Challenge that asks the replacement (none while only
  an Upcoming one does).

**Streaks and Result Cards** (`streak`, `result_card`, #18). A Streak is never stored: it is
counted from the plays each time (`streak_length` is the rule), so no import or replay can
change it. A Result Card is a finished play's score and marks, never its Questions or answers.

**The Archive and Catch-up** (`archive`, `catch_up`, #19): every released Challenge of a Stack
with the Learner's play of it, newest first; and, across their Active Stacks, the past ones they
haven't finished. Catch-up is optional and never blocks anything.
"""

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.content.challenges import ChallengesAhead, is_frozen
from app.content.challenges import challenges_ahead as days_ahead
from app.grading import Grader, GradingFailed
from app.marking import mark
from app.models import Answer, ChallengePlay, DailyChallenge, LearnerStack, Question, Stack
from app.review import utc_day

DAILY_CHALLENGE = "daily_challenge"
"""`Answer.context` for the first answer to a Question of a Daily Challenge."""

Outcome = Literal["correct", "wrong", "ungraded"]
"""How a Question went: the first try's outcome, or a later answer's mark."""

Status = Literal["not_started", "in_progress", "finished"]


@dataclass(frozen=True)
class StackChallengesAhead:
    stack: Stack
    ahead: ChallengesAhead


def challenges_ahead(session: Session, today: date) -> list[StackChallengesAhead]:
    """Every Stack with a Syllabus, by name, with how far ahead its Challenges are written from
    `today` (UTC). A Stack with none written has 0 Days left."""
    last: dict[str, date] = {
        stack_id: day
        for stack_id, day in session.execute(
            select(DailyChallenge.stack_id, func.max(DailyChallenge.day)).group_by(
                DailyChallenge.stack_id
            )
        )
    }
    stacks = session.scalars(
        select(Stack).where(Stack.current_syllabus_pk.is_not(None)).order_by(Stack.name)
    )
    return [
        StackChallengesAhead(s, days_ahead([last[s.id]] if s.id in last else [], today))
        for s in stacks
    ]


# --- Playing ---------------------------------------------------------------------------------


class ChallengeNotFound(Exception):
    """No such Challenge on the Stack, or it isn't released yet: the same to a Learner."""


class QuestionNotInChallenge(Exception):
    def __init__(self, question_id: str) -> None:
        super().__init__(question_id)
        self.question_id = question_id


class QuestionRetired(Exception):
    def __init__(self, question_id: str) -> None:
        super().__init__(question_id)
        self.question_id = question_id


def outcome(correct: bool | None) -> Outcome:
    """A marked or recorded answer's outcome: `correct` null is ungraded."""
    return "ungraded" if correct is None else "correct" if correct else "wrong"


@dataclass(frozen=True)
class Replacement:
    """The Question that replaces a Retired Question."""

    question_id: str
    challenge: DailyChallenge | None
    """The first released Challenge that asks it, or None if none does yet."""


@dataclass(frozen=True)
class ChallengeQuestion:
    question: Question
    """Includes the correct answer: never send it unless `first_try` is set."""
    first_try: Answer | None
    """The Learner's scored answer, if they have given it."""
    replacement: Replacement | None = None
    """A Retired Question's replacement, if it has one."""

    @property
    def answerable(self) -> bool:
        """Whether it still waits for a first answer: a Retired Question never gets one."""
        return self.first_try is None and not self.question.retired


@dataclass(frozen=True)
class ChallengeState:
    """A released Challenge as one Learner has played it."""

    challenge: DailyChallenge
    play: ChallengePlay | None
    questions: list[ChallengeQuestion]
    """In the order they are asked."""

    @property
    def status(self) -> Status:
        if self.play is None:
            return "not_started"
        return "in_progress" if self.play.finished_at is None else "finished"


@dataclass(frozen=True)
class ChallengeAnswer:
    question: Question
    response: str | None
    outcome: Outcome
    feedback: str | None
    """The grader's one line, for a graded written answer."""
    counted: bool
    """True only for the first answer to the Question, which is the one scored."""
    state: ChallengeState
    """The Challenge after this answer."""


def todays_challenge(session: Session, stack_id: str, now: datetime) -> DailyChallenge | None:
    """The Stack's Daily Challenge for the Day `now` falls on (UTC), or None if none is
    written for it. It was released at 00:00 UTC."""
    return session.scalar(
        select(DailyChallenge).where(
            DailyChallenge.stack_id == stack_id, DailyChallenge.day == utc_day(now)
        )
    )


def challenge_state(
    session: Session, record: LearnerStack, challenge: DailyChallenge, now: datetime
) -> ChallengeState:
    """The Learner's play of `challenge` (a released one). A play left with nothing to answer,
    because a Question was retired while it was under way, is finished now."""
    play = _play(session, record, challenge.number)
    state = _state(session, challenge, play, now)
    if play is not None and play.finished_at is None and _finish_if_done(state, now):
        session.commit()
    return state


def answer(
    session: Session,
    record: LearnerStack,
    number: int,
    question_id: str,
    response: str | None,
    grader: Grader,
    now: datetime,
) -> ChallengeAnswer:
    """Mark the Learner's answer to one Question of Challenge #`number`: a choice ID or a
    written answer (None, or a blank one, is unanswered, so wrong). The first answer to the
    Question is recorded and scored, even when grading it fails (ungraded); any other is marked
    and recorded nowhere.

    Raises ChallengeNotFound, QuestionNotInChallenge, QuestionRetired,
    NotAChoice or AnswerTooLong, and GradingFailed for an answer that doesn't count; nothing is
    recorded then.

    Grading (up to 45 s) runs before any lock is taken, so the Learner's other answers on the
    Stack never wait on it. Only recording a first try locks the Learner's record on the Stack,
    and it checks again under the lock: when a double submission already recorded this
    Question's first try, this answer is marked like any later one and counts for nothing.
    """
    challenge = _playable(session, record, number, now)
    state = _state(session, challenge, _play(session, record, number), now)
    asked = next((q for q in state.questions if q.question.id == question_id), None)
    if asked is None:
        raise QuestionNotInChallenge(question_id)
    if asked.question.retired:
        raise QuestionRetired(question_id)
    question = asked.question
    if asked.first_try is not None:
        marked = mark(question, response, grader)
        return ChallengeAnswer(
            question, response, outcome(marked.correct), marked.feedback, counted=False, state=state
        )

    correct: bool | None
    try:
        first = mark(question, response, grader)
        correct, feedback = first.correct, first.feedback
    except GradingFailed:
        correct, feedback = None, None  # ungraded: the first try is spent

    session.rollback()  # end the reads; the lock below starts a fresh transaction
    session.execute(
        select(LearnerStack.learner_id)
        .where(
            LearnerStack.learner_id == record.learner_id,
            LearnerStack.stack_id == record.stack_id,
        )
        .with_for_update()
    )
    play = _play(session, record, number)
    state = _state(session, challenge, play, now)
    asked = next(q for q in state.questions if q.question.id == question_id)
    if asked.first_try is not None:
        session.commit()  # releases the lock; another request recorded the first try
        if correct is None:
            raise GradingFailed("grading failed, and the first try was already recorded")
        return ChallengeAnswer(
            question, response, outcome(correct), feedback, counted=False, state=state
        )

    if play is None:
        play = ChallengePlay(
            learner_id=record.learner_id,
            stack_id=record.stack_id,
            challenge_number=number,
            started_at=now,
        )
        session.add(play)
        session.flush()
    session.add(
        Answer(
            learner_id=record.learner_id,
            stack_id=record.stack_id,
            question_id=question_id,
            context=DAILY_CHALLENGE,
            challenge_play_id=play.id,
            response=response,
            correct=correct,
            feedback=feedback,
            answered_at=now,
        )
    )
    session.flush()
    state = _state(session, challenge, play, now)
    _finish_if_done(state, now)
    session.commit()
    return ChallengeAnswer(
        question, response, outcome(correct), feedback, counted=True, state=state
    )


def played_question_ids(session: Session, learner_id: int, stack_id: str) -> list[str]:
    """The Questions of the Challenges the Learner has finished on the Stack, oldest Challenge
    first. An unfinished play's Questions aren't played yet: Review must not ask them first."""
    rows = session.scalars(
        select(DailyChallenge.question_ids)
        .join(
            ChallengePlay,
            (ChallengePlay.stack_id == DailyChallenge.stack_id)
            & (ChallengePlay.challenge_number == DailyChallenge.number),
        )
        .where(
            ChallengePlay.learner_id == learner_id,
            ChallengePlay.stack_id == stack_id,
            ChallengePlay.finished_at.is_not(None),
        )
        .order_by(DailyChallenge.number)
    )
    return list(dict.fromkeys(qid for ids in rows for qid in ids))


# --- The Archive and Catch-up (#19) ----------------------------------------------------------


@dataclass(frozen=True)
class ArchivedChallenge:
    """A released Challenge in the Archive, with the Learner's play of it, if any."""

    challenge: DailyChallenge
    play: ChallengePlay | None

    @property
    def status(self) -> Status:
        if self.play is None:
            return "not_started"
        return "in_progress" if self.play.finished_at is None else "finished"


@dataclass(frozen=True)
class StackCatchUp:
    record: LearnerStack
    challenges: list[ArchivedChallenge]
    """Newest first."""


def archive(session: Session, record: LearnerStack, now: datetime) -> list[ArchivedChallenge]:
    """Every released Challenge of the Learner's Active Stack, back to #1, newest first, with
    their play of each. An Upcoming Challenge is never in it."""
    rows = session.execute(
        select(DailyChallenge, ChallengePlay)
        .outerjoin(
            ChallengePlay,
            (ChallengePlay.stack_id == DailyChallenge.stack_id)
            & (ChallengePlay.challenge_number == DailyChallenge.number)
            & (ChallengePlay.learner_id == record.learner_id),
        )
        .where(
            DailyChallenge.stack_id == record.stack_id,
            DailyChallenge.day <= utc_day(now),  # released (`is_frozen`)
        )
        .order_by(DailyChallenge.day.desc())
    )
    return [ArchivedChallenge(c, play) for c, play in rows]


def catch_up(
    session: Session, records: Sequence[LearnerStack], now: datetime
) -> list[StackCatchUp]:
    """For each of the Learner's Active Stacks, in the order given: the Archive's past
    Challenges they haven't finished, newest first. Today's is left out: it is home's."""
    today = utc_day(now)
    return [
        StackCatchUp(
            r,
            [
                a
                for a in archive(session, r, now)
                if a.challenge.day != today and a.status != "finished"
            ],
        )
        for r in records
    ]


def released_challenge(
    session: Session, stack_id: str, number: int, now: datetime
) -> DailyChallenge | None:
    """Challenge #`number` of the Stack, or None if there is none or it isn't released yet."""
    challenge = session.scalar(
        select(DailyChallenge).where(
            DailyChallenge.stack_id == stack_id, DailyChallenge.number == number
        )
    )
    if challenge is None or not is_frozen(challenge.day, utc_day(now)):
        return None
    return challenge


def _playable(session: Session, record: LearnerStack, number: int, now: datetime) -> DailyChallenge:
    challenge = released_challenge(session, record.stack_id, number, now)
    if challenge is None:
        raise ChallengeNotFound(number)
    return challenge


def _play(session: Session, record: LearnerStack, number: int) -> ChallengePlay | None:
    return session.scalar(
        select(ChallengePlay).where(
            ChallengePlay.learner_id == record.learner_id,
            ChallengePlay.stack_id == record.stack_id,
            ChallengePlay.challenge_number == number,
        )
    )


def _state(
    session: Session, challenge: DailyChallenge, play: ChallengePlay | None, now: datetime
) -> ChallengeState:
    questions = _questions(session, challenge.stack_id, challenge.question_ids)
    first: dict[str, Answer] = {}
    if play is not None:
        first = {
            a.question_id: a
            for a in session.scalars(select(Answer).where(Answer.challenge_play_id == play.id))
        }
    return ChallengeState(
        challenge,
        play,
        [ChallengeQuestion(q, first.get(q.id), _replacement(session, q, now)) for q in questions],
    )


def _replacement(session: Session, question: Question, now: datetime) -> Replacement | None:
    if question.replaced_by is None:
        return None
    first_asking = session.scalar(
        select(DailyChallenge)
        .where(
            DailyChallenge.stack_id == question.stack_id,
            DailyChallenge.question_ids.contains([question.replaced_by]),
            DailyChallenge.day <= utc_day(now),  # released (`is_frozen`)
        )
        .order_by(DailyChallenge.number)
        .limit(1)
    )
    return Replacement(question.replaced_by, first_asking)


def _finish_if_done(state: ChallengeState, now: datetime) -> bool:
    """Finish the play once no Question waits for a first answer. Returns whether it did."""
    play = state.play
    if play is None or play.finished_at is not None:
        return False
    if any(q.answerable for q in state.questions):
        return False
    first_tries = [q.first_try for q in state.questions if q.first_try is not None]
    play.finished_at = now
    play.finished_day = utc_day(now)
    play.on_its_day = play.finished_day == state.challenge.day
    play.score = sum(1 for a in first_tries if a.correct)
    play.out_of = len(first_tries)
    return True


def _questions(session: Session, stack_id: str, question_ids: Sequence[str]) -> list[Question]:
    """The Challenge's Questions in order, with their Sources and Materials, retired or not."""
    rows = session.scalars(
        select(Question)
        .where(Question.stack_id == stack_id, Question.id.in_(question_ids))
        .options(selectinload(Question.sources), selectinload(Question.material_links))
    ).all()
    by_id = {q.id: q for q in rows}
    return [by_id[qid] for qid in question_ids]


# --- Streaks and Result Cards (#18) ----------------------------------------------------------


def streak_length(challenge_days: Iterable[date], played: Collection[date], today: date) -> int:
    """The Streak rule. Walking back from `today` over the Days that have a released Challenge
    (`challenge_days`; later ones are ignored), count each whose Challenge the Learner played on
    its Day (`played`), and stop at the first they didn't: missing a Day resets the Streak to 0.
    A Day with no Challenge is skipped, so it neither extends nor breaks it. Today's Challenge,
    until it is played, doesn't break it either: the Streak is still yesterday's run.

    So a Streak can't start before the Learner's first play: every Day before it is unplayed."""
    count = 0
    for day in sorted((d for d in challenge_days if d <= today), reverse=True):
        if day in played:
            count += 1
        elif day != today:
            break
    return count


def streak(session: Session, learner_id: int, stack_id: str, now: datetime) -> int:
    """The Learner's Streak on the Stack at `now` (UTC Days). A Day counts only if its play was
    *finished* on the Challenge's own Day (`ChallengePlay.on_its_day`): a play started at 23:59
    and finished after midnight doesn't count, nor does any play from the Archive (#19).

    A Day whose Challenge has every Question retired can't be played, so it is skipped like a
    Day with no Challenge, unless the Learner had played it already."""
    today = utc_day(now)
    retired = set(
        session.scalars(
            select(Question.id).where(
                Question.stack_id == stack_id, Question.retired_reason.is_not(None)
            )
        )
    )
    days = [
        day
        for day, question_ids in session.execute(
            select(DailyChallenge.day, DailyChallenge.question_ids).where(
                DailyChallenge.stack_id == stack_id, DailyChallenge.day <= today
            )
        )
        if not set(question_ids) <= retired
    ]
    played = set(
        session.scalars(
            select(DailyChallenge.day)
            .join(
                ChallengePlay,
                (ChallengePlay.stack_id == DailyChallenge.stack_id)
                & (ChallengePlay.challenge_number == DailyChallenge.number),
            )
            .where(
                ChallengePlay.learner_id == learner_id,
                ChallengePlay.stack_id == stack_id,
                ChallengePlay.on_its_day.is_(True),
            )
        )
    )
    return streak_length({*days, *played}, played, today)


RESULT_MARKS: dict[Outcome, str] = {"correct": "✅", "wrong": "❌", "ungraded": "⬜"}
"""A Result Card's mark for each first try: ungraded is a written answer whose grading failed."""


def result_card(label: str, state: ChallengeState) -> str | None:
    """The Result Card of a finished play, as text to share: the Challenge's `label` (Stack,
    number and UTC Day), the score, and a mark per answered Question in Challenge order:
    "Agentic AI Engineer #40 · 26 Sep · 2/3 ✅❌✅". A Retired Question that was never answered
    isn't scored, so it has no mark. None until the play is finished."""
    play = state.play
    if play is None or play.finished_at is None:
        return None
    marks = "".join(
        RESULT_MARKS[outcome(q.first_try.correct)]
        for q in state.questions
        if q.first_try is not None
    )
    return f"{label} · {play.score}/{play.out_of} {marks}"
