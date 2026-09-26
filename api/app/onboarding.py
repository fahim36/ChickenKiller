"""A Learner's Active Stack and time zone: chosen at onboarding, changed later in settings.

Choosing a Stack for the first time creates the Learner's record on it (`LearnerStack`), which
their progress on that Stack hangs off. Switching to another Stack keeps that record, so
switching back resumes it.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Learner, LearnerStack, Stack


class NotPublished(Exception):
    """The Stack doesn't exist or isn't on the published list."""


def needs_onboarding(learner: Learner) -> bool:
    return learner.active_stack_id is None or learner.time_zone is None


def today_for(time_zone: str, now: datetime) -> date:
    """The calendar day it is at `now` (timezone-aware) in the IANA `time_zone`."""
    return now.astimezone(ZoneInfo(time_zone)).date()


def active_stack(session: Session, learner: Learner) -> LearnerStack | None:
    """The Learner's record on their Active Stack, or None before onboarding."""
    if learner.active_stack_id is None:
        return None
    return session.get(LearnerStack, (learner.id, learner.active_stack_id))


def choose(session: Session, learner: Learner, stack_id: str, time_zone: str) -> LearnerStack:
    """Make `stack_id` the Learner's Active Stack and save their time zone (an IANA name that
    the caller has checked).

    Only a published Stack can be chosen. A Learner whose Active Stack was later withdrawn keeps
    it, so they can still save their time zone without switching.
    """
    stack = session.scalar(
        select(Stack).where(Stack.id == stack_id, Stack.current_syllabus_pk.is_not(None))
    )
    if stack is None or not (stack.published or stack.id == learner.active_stack_id):
        raise NotPublished(stack_id)

    record = session.get(LearnerStack, (learner.id, stack.id))
    if record is None:
        record = LearnerStack(learner_id=learner.id, stack=stack, started_at=datetime.now(UTC))
        session.add(record)
    learner.active_stack_id = stack.id
    learner.time_zone = time_zone
    session.commit()
    return record
