"""The Daily Review rules: which day a Review Round belongs to, when it opens and when it
becomes a Pending Review Round, what carries over from a day with rounds left unfinished, when
a Missed Question leaves the rotation, and which Questions a round asks.

Plain functions with no database or HTTP, tested directly (tests/test_review_rules.py). The
clock (`now`, timezone-aware) and the random source (`rng`) are passed in, so a test can say
"it is 23:59 UTC" without waiting. `app/reviews.py` stores what
these decide.

The round state machine: not open -> open ("optional") -> "pending" -> "finished", or dropped
at the end of its day if not finished.

- A **Daily Review** belongs to one Day, a UTC calendar day (`review_day`, ADR-0005).
  Round 1 opens the first time the Learner uses the app that Day.
- **Rounds 2 and 3** each open `REOPEN_AFTER` (four hours) after the previous round is
  finished (`next_round_opens_at`), never more than `ROUNDS_PER_DAY` in a day, and only while
  the opening time is still on that day. A round opens at that time whether or not the Learner
  is using the app then: `app/reviews.py` stores it lazily on the next request, with the true
  opening time, so it is pending two hours after that.
- A **Review Round** is optional for `OPTIONAL_PERIOD` (two hours) after it opens, then it is a
  **Pending Review Round** until it's finished (`round_state`). A round only opens once the one
  before it is finished, so there is never more than one Pending Review Round.
- **Dropped rounds**: rounds not finished by the end of their day are dropped. Their unanswered
  Questions (`carried_over`) come first in the Learner's next day with rounds.
- **The rotation** (`in_rotation`): a Missed Question stays in the rotation until it has been
  answered correctly on `ROTATION_DAYS` (three) different Days since it was last missed.
- A round asks up to `ROUND_SIZE` Questions (`pick_round_questions`) from its `RoundSources`, in
  order: carried-over Questions, Missed Questions still in the rotation, Updated Lessons' new
  Questions (#13), then Questions from Completed Lessons at random. A Question already asked
  earlier that day is left out, unless the round would otherwise be short.
- **The Streak** (`streak`, #11): the consecutive days on which the Learner finished their
  whole Daily Review (`day_outcome`). A past day with a round left unfinished, or not used at
  all, resets it to zero; a day with nothing owed, and today while still in progress, neither
  extend nor break it.
"""

import random
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal

ROUND_SIZE = 10
"""The most Questions a Review Round asks."""

OPTIONAL_PERIOD = timedelta(hours=2)
"""How long a Review Round stays optional after it opens."""

REOPEN_AFTER = timedelta(hours=4)
"""How long after a round is finished the next round of the day opens."""

ROUNDS_PER_DAY = 3
"""The most Review Rounds in one Daily Review."""

ROTATION_DAYS = 3
"""On how many different days a Missed Question must be answered correctly to leave the
rotation."""

RoundState = Literal["optional", "pending", "finished"]


def review_day(now: datetime) -> date:
    """The Day whose Daily Review `now` (timezone-aware) falls in: its calendar day in UTC."""
    return now.astimezone(UTC).date()


def pending_at(opened_at: datetime) -> datetime:
    """When a round that opened at `opened_at` becomes a Pending Review Round, unless finished."""
    return opened_at + OPTIONAL_PERIOD


def round_state(opened_at: datetime, finished_at: datetime | None, now: datetime) -> RoundState:
    """A Review Round's state at `now`: "finished" once every Question is answered, otherwise
    "optional" for its first two hours and "pending" from exactly two hours after it opened."""
    if finished_at is not None:
        return "finished"
    return "pending" if now >= pending_at(opened_at) else "optional"


def next_round_opens_at(finished_ats: Sequence[datetime | None], day: date) -> datetime | None:
    """When the next Review Round of `day` opens, given the `finished_at` of the day's rounds so
    far, in order: four hours after the last one is finished.

    None when no further round opens that day: no round yet (Round 1 opens on the day's first
    use instead), the last one isn't finished, the day already has three rounds, or the opening
    time falls after the Day's end (00:00 UTC).

    #11: a day's rounds were all finished when every round is finished and this is None, since
    a round that opened with nobody using the app is only stored on the next request.
    """
    if not finished_ats or len(finished_ats) >= ROUNDS_PER_DAY:
        return None
    last = finished_ats[-1]
    if last is None:
        return None
    opens_at = last + REOPEN_AFTER
    return opens_at if review_day(opens_at) == day else None


def carried_over(unfinished: Iterable[tuple[Sequence[str], Collection[str]]]) -> list[str]:
    """The Questions a day's unfinished (dropped) rounds carry over: each round's Questions (in
    the order asked) minus those it answered, given as `(question_ids, answered_ids)` in round
    order. Each Question once."""
    carried = (
        q for question_ids, answered in unfinished for q in question_ids if q not in answered
    )
    return list(dict.fromkeys(carried))


def in_rotation(last_missed_at: datetime, correct_at: Iterable[datetime]) -> bool:
    """Whether a Missed Question is still in the rotation: it hasn't been answered correctly on
    three different Days since it was last missed (`last_missed_at`). Correct
    answers anywhere count (Lesson Quiz, Retake, Review Round); several on one day count once,
    and the day of the miss counts for a correct answer given after it. A later miss starts the
    count again."""
    days = {review_day(at) for at in correct_at if at > last_missed_at}
    return len(days) < ROTATION_DAYS


@dataclass(frozen=True)
class RoundSources:
    """Where a Review Round's Questions (permanent IDs) come from, in the order they are used."""

    carried_over: Sequence[str] = ()
    """Unanswered Questions of the rounds dropped on the Learner's previous day with rounds."""
    missed: Sequence[str] = ()
    """Missed Questions still in the rotation, first missed first."""
    updated: Sequence[str] = ()
    """New Questions of Updated Lessons (#13)."""
    completed: Sequence[str] = ()
    """Questions of Completed Lessons: the random fill."""
    asked_today: Collection[str] = frozenset()
    """Questions already asked in the day's earlier rounds."""


def pick_round_questions(
    sources: RoundSources, rng: random.Random, size: int = ROUND_SIZE
) -> list[str]:
    """A Review Round's Questions (permanent IDs), in the order they are asked.

    - `carried_over`, then `missed`, then `updated` come first, each in its own order, up to
      `size`.
    - The rest is filled at random from `completed`.
    - Questions in `asked_today` are left out. If that leaves the round short, it is topped up
      at random with Questions of `completed` that were asked earlier today.
    - No Question is asked twice. With fewer Questions than `size`, the round asks them all;
      with none, it's empty.
    """
    asked = set(sources.asked_today)
    ordered = [
        q
        for q in dict.fromkeys([*sources.carried_over, *sources.missed, *sources.updated])
        if q not in asked
    ]
    picked = ordered[:size]
    taken = set(picked)
    completed = [q for q in dict.fromkeys(sources.completed) if q not in taken]
    fresh = [q for q in completed if q not in asked]
    picked += rng.sample(fresh, min(size - len(picked), len(fresh)))
    repeats = [q for q in completed if q in asked]
    return picked + rng.sample(repeats, min(size - len(picked), len(repeats)))


DayOutcome = Literal["finished", "unfinished", "nothing_owed", "in_progress"]
"""How one day's Daily Review went, for the Streak."""


def day_outcome(finished_ats: Sequence[datetime | None], day: date, today: date) -> DayOutcome:
    """How the Daily Review of `day`, a day the Learner used the app, went by `today`, given the
    `finished_at` of the day's stored rounds in order.

    - "nothing_owed": no round opened (the Learner had no Completed Lesson at the day's first use).
    - "finished": every round is finished and no further round opens that day
      (`next_round_opens_at`). Rows alone aren't enough: a round that came due while the Learner
      was away is never stored.
    - "in_progress": today, not finished yet.
    - "unfinished": a past day, not finished.
    """
    if not finished_ats:
        return "nothing_owed"
    if all(finished_ats) and next_round_opens_at(finished_ats, day) is None:
        return "finished"
    return "in_progress" if day == today else "unfinished"


def streak(days: Mapping[date, DayOutcome], today: date) -> int:
    """The Streak on `today`: the finished days since the last unfinished one.

    `days` holds the outcome of each day the Learner used the app (`day_outcome`). A day with
    nothing owed neither extends nor breaks the Streak, and nor does today while in progress
    (or not yet used). A past day missing from `days`, on which the Learner never used the app,
    breaks it: its Round 1 was owed but never opened. Before the Learner's first day with
    rounds the Streak is zero anyway, so such a day costs nothing there.
    """
    count = 0
    if not days:
        return count
    day = min(days)
    while day <= today:
        outcome = days.get(day, "in_progress" if day == today else "unfinished")
        if outcome == "finished":
            count += 1
        elif outcome == "unfinished":
            count = 0
        day += timedelta(days=1)
    return count
