"""The Review rules: which Questions are due, and in what order the queue asks them.

Review is optional: a queue the Learner practises from, in sets of up to `SET_SIZE`, whenever
they like, across all their Active Stacks. It has no rounds or timers and never blocks anything
(ADR-0003). Plain functions with no database or HTTP, tested directly
(tests/test_review_rules.py). The day (`today`, a UTC Day, ADR-0005) is passed in, so a test can
say "it is the next day" without waiting. `app/reviews.py` gathers the Learner's data into
`ReviewSources` and asks these.

- **Missed Questions** come first, oldest (first missed) first, across Active Stacks. A Missed
  Question leaves the queue once answered correctly on `CORRECT_DAYS` (three) different Days
  since it was last missed (`in_queue`). Until then it is due every Day, except that once it
  has been answered correctly today it waits for tomorrow, since another correct answer today
  couldn't count towards a new Day (`missed_is_due`).
- **Updated Lessons' new Questions** (#13) come next, in Syllabus order, until answered.
- **Spaced repeats** come last: Questions of Completed Lessons and of played Daily Challenges
  that weren't answered, anywhere, in the last `SPACING_DAYS` (three) Days (`repeat_is_due`).
  Least recently answered first; a Question never answered counts as the least recent. Ties
  keep the order they were given in (Stack, then Syllabus order).
- Each Question is queued once, in its first place (`queue`). A set is the first `SET_SIZE`.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import NamedTuple

SET_SIZE = 10
"""The most Questions a Review set asks."""

CORRECT_DAYS = 3
"""On how many different Days a Missed Question must be answered correctly to leave the queue."""

SPACING_DAYS = 3
"""How many Days a spaced repeat waits after it was last answered: one answered on the 26th is
due again on the 29th."""


def utc_day(at: datetime) -> date:
    """The Day `at` (timezone-aware) falls on: its calendar day in UTC."""
    return at.astimezone(UTC).date()


def in_queue(last_missed_at: datetime, correct_at: Iterable[datetime]) -> bool:
    """Whether a Missed Question is still in the queue: it hasn't been answered correctly on
    three different Days since it was last missed (`last_missed_at`). Correct answers anywhere
    count (Lesson Quiz, Retake, Review); several on one Day count once, and the Day of the miss
    counts for a correct answer given after it. A later miss starts the count again."""
    days = {utc_day(at) for at in correct_at if at > last_missed_at}
    return len(days) < CORRECT_DAYS


def missed_is_due(last_missed_at: datetime, correct_at: Iterable[datetime], today: date) -> bool:
    """Whether a Missed Question is due in Review `today`: still in the queue, and not answered
    correctly yet today since it was last missed."""
    correct = [at for at in correct_at if at > last_missed_at]
    return in_queue(last_missed_at, correct) and all(utc_day(at) != today for at in correct)


def repeat_is_due(last_answered_at: datetime | None, today: date) -> bool:
    """Whether a spaced repeat is due `today`: never answered, or last answered (anywhere) at
    least `SPACING_DAYS` Days ago."""
    return last_answered_at is None or (today - utc_day(last_answered_at)).days >= SPACING_DAYS


class QuestionRef(NamedTuple):
    """A Question in Review, which spans Stacks: its Stack and permanent ID."""

    stack_id: str
    question_id: str


@dataclass(frozen=True)
class Missed:
    """A Missed Question, with the Learner's correct answers to it (any time, any context)."""

    ref: QuestionRef
    first_missed_at: datetime
    last_missed_at: datetime
    correct_at: Sequence[datetime]


@dataclass(frozen=True)
class Repeat:
    """A Question that can come back as a spaced repeat, and when the Learner last answered it."""

    ref: QuestionRef
    last_answered_at: datetime | None


@dataclass(frozen=True)
class ReviewSources:
    """Where the Review queue's Questions come from, in the order they are used."""

    missed: Sequence[Missed] = ()
    """The Learner's Missed Questions, in any order: the queue sorts them oldest first."""
    updated: Sequence[QuestionRef] = ()
    """New Questions of Updated Lessons not answered yet (#13), in Syllabus order."""
    repeats: Sequence[Repeat] = ()
    """Questions of Completed Lessons and played Daily Challenges, in Stack then Syllabus
    order."""


def queue(sources: ReviewSources, today: date) -> list[QuestionRef]:
    """The whole Review queue `today`, in the order it is asked: due Missed Questions oldest
    first, then the Updated Lessons' new Questions, then due spaced repeats least recently
    answered first. Each Question once. A set is its first `SET_SIZE`."""
    missed = sorted(
        (m for m in sources.missed if missed_is_due(m.last_missed_at, m.correct_at, today)),
        key=lambda m: m.first_missed_at,
    )
    repeats = sorted(
        (r for r in sources.repeats if repeat_is_due(r.last_answered_at, today)),
        key=lambda r: (r.last_answered_at is not None, r.last_answered_at or datetime.min),
    )
    # A Missed Question that has left the queue can still come back as a repeat. One answered
    # correctly today can't: that answer makes it a repeat answered today.
    return list(
        dict.fromkeys([*(m.ref for m in missed), *sources.updated, *(r.ref for r in repeats)])
    )
