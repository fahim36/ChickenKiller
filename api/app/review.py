"""The Daily Review rules: which day a Review Round belongs to, when it becomes a Pending Review
Round, and which Questions it asks.

Plain functions with no database or HTTP, tested directly (tests/test_review_rules.py). The
clock (`now`, timezone-aware) and the random source (`rng`) are passed in, so a test can say
"it is 23:59 in Dhaka" without waiting. `app/reviews.py` stores what these decide.

- A **Daily Review** belongs to one calendar day in the Learner's own time zone
  (`review_day`). Round 1 opens the first time the Learner uses the app that day.
- A **Review Round** is optional for `OPTIONAL_PERIOD` (two hours) after it opens, then it is a
  **Pending Review Round** until it's finished (`round_state`). Only rounds of the Learner's
  current day count: #10 drops unfinished rounds at the end of their day.
- A round asks up to `ROUND_SIZE` Questions (`pick_round_questions`): Missed Questions first,
  then Questions from Completed Lessons at random.

Kept ready for #10: `ROUNDS_PER_DAY` bounds a round's `number`; Rounds 2 and 3 open four hours
after the previous one is finished and use the same `round_state`; carried-over Questions go at
the front of `missed_ids`.
"""

import random
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import Literal

from app.onboarding import today_for

ROUND_SIZE = 10
"""The most Questions a Review Round asks."""

OPTIONAL_PERIOD = timedelta(hours=2)
"""How long a Review Round stays optional after it opens."""

ROUNDS_PER_DAY = 3
"""The most Review Rounds in one Daily Review (#10 opens Rounds 2 and 3)."""

RoundState = Literal["optional", "pending", "finished"]


def review_day(time_zone: str, now: datetime) -> date:
    """The day whose Daily Review `now` falls in: the calendar day in the IANA `time_zone`."""
    return today_for(time_zone, now)


def pending_at(opened_at: datetime) -> datetime:
    """When a round that opened at `opened_at` becomes a Pending Review Round, unless finished."""
    return opened_at + OPTIONAL_PERIOD


def round_state(opened_at: datetime, finished_at: datetime | None, now: datetime) -> RoundState:
    """A Review Round's state at `now`: "finished" once every Question is answered, otherwise
    "optional" for its first two hours and "pending" from exactly two hours after it opened."""
    if finished_at is not None:
        return "finished"
    return "pending" if now >= pending_at(opened_at) else "optional"


def pick_round_questions(
    missed_ids: Sequence[str],
    completed_lesson_question_ids: Sequence[str],
    rng: random.Random,
    size: int = ROUND_SIZE,
) -> list[str]:
    """A Review Round's Questions (permanent IDs), in the order they are asked.

    - `missed_ids` (the Learner's Missed Questions, first missed first) come first, in that
      order, up to `size`.
    - The rest is filled at random from `completed_lesson_question_ids`, the Questions of the
      Learner's Completed Lessons.
    - No Question is asked twice. With fewer Questions than `size`, the round asks them all;
      with none, it's empty.
    """
    picked = list(dict.fromkeys(missed_ids))[:size]
    taken = set(picked)
    rest = [q for q in dict.fromkeys(completed_lesson_question_ids) if q not in taken]
    return picked + rng.sample(rest, min(size - len(picked), len(rest)))
