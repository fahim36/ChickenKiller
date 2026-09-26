"""Daily Challenges, as imported (#16). For now only the Admin's view: how far ahead each Stack's
Challenges are written. An Upcoming Challenge's Questions are never read here, so nothing about
them can reach a Learner."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.challenges import ChallengesAhead
from app.content.challenges import challenges_ahead as days_ahead
from app.models import DailyChallenge, Stack


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
