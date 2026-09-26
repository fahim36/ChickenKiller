"""The Daily Challenge rules shared by the content check, the importer and the Admin page.

All Days are UTC Days (ADR-0005). An Upcoming Challenge can be edited until its Day; a Challenge
whose Day has passed is released and frozen. A Day with no Challenge written has no Challenge.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

MIN_DAYS_AHEAD = 3
"""Fewer Days than this left written is a warning, in the content check and on the Admin page."""


def challenge_day(launch: date, number: int) -> date:
    """Challenge #n is on the launch Day plus n - 1 Days."""
    return launch + timedelta(days=number - 1)


def is_frozen(day: date, today: date) -> bool:
    """A Challenge whose Day is before `today` (UTC) is released: it never changes again, and a
    Day that has passed can't get one."""
    return day < today


@dataclass(frozen=True)
class ChallengesAhead:
    """How far ahead a Stack's Challenges are written: through the last one's Day, counting
    Days from today (UTC) to it, both included. A gap before it doesn't count against it."""

    written_through: date | None
    days_left: int

    @property
    def warning(self) -> bool:
        return self.days_left < MIN_DAYS_AHEAD

    def __str__(self) -> str:
        days = f"{self.days_left} Day{'' if self.days_left == 1 else 's'} left"
        if self.written_through is None:
            return f"No Challenges written ({days})"
        return f"Challenges written through {self.written_through.isoformat()} ({days})"


def challenges_ahead(days: Iterable[date], today: date) -> ChallengesAhead:
    last = max(days, default=None)
    if last is None:
        return ChallengesAhead(None, 0)
    return ChallengesAhead(last, max(0, (last - today).days + 1))
