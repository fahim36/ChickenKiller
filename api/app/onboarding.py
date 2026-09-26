"""A Learner's Active Stacks: picked at onboarding, activated and deactivated later in settings.

Activating a Stack for the first time creates the Learner's record on it (`LearnerStack`), which
their progress on that Stack hangs off. Deactivating a Stack only marks that record inactive, so
reactivating it resumes where the Learner left off.

A Learner always keeps at least one Active Stack once onboarded: saving none is refused
(`NoStack`), so deactivating the last one means activating another in the same save.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Learner, LearnerStack, Stack


class NotPublished(Exception):
    """The Stack doesn't exist or isn't on the published list."""


class NoStack(Exception):
    """No Stack was picked: a Learner needs at least one Active Stack."""


def active_stacks(session: Session, learner: Learner) -> list[LearnerStack]:
    """The Learner's records on their Active Stacks, the first started first. Empty before
    onboarding."""
    return list(
        session.scalars(
            select(LearnerStack)
            .where(LearnerStack.learner_id == learner.id, LearnerStack.active)
            .order_by(LearnerStack.started_at, LearnerStack.stack_id)
        )
    )


def needs_onboarding(session: Session, learner: Learner) -> bool:
    return not active_stacks(session, learner)


def active_stack(session: Session, learner: Learner, stack_id: str) -> LearnerStack | None:
    """The Learner's record on `stack_id` if it is one of their Active Stacks, else None."""
    record = session.get(LearnerStack, (learner.id, stack_id))
    return record if record is not None and record.active else None


def set_active_stacks(session: Session, learner: Learner, stack_ids: list[str]) -> None:
    """Make exactly `stack_ids` the Learner's Active Stacks: activate each (creating its record
    the first time) and deactivate the rest, keeping their records and progress.

    At least one Stack must be picked (`NoStack`), and each must be a published Stack
    (`NotPublished`), except that a Learner keeps an Active Stack the Admin has since withdrawn.
    Once deactivated, a withdrawn Stack can't be activated again. Nothing changes on a refusal.
    """
    wanted = list(dict.fromkeys(stack_ids))
    if not wanted:
        raise NoStack()
    records = {
        r.stack_id: r
        for r in session.scalars(select(LearnerStack).where(LearnerStack.learner_id == learner.id))
    }
    stacks = {
        s.id: s
        for s in session.scalars(
            select(Stack).where(Stack.id.in_(wanted), Stack.current_syllabus_pk.is_not(None))
        )
    }
    for stack_id in wanted:
        stack, record = stacks.get(stack_id), records.get(stack_id)
        if stack is None or not (stack.published or (record is not None and record.active)):
            raise NotPublished(stack_id)

    for stack_id, record in records.items():
        record.active = stack_id in wanted
    for stack_id in wanted:
        if stack_id not in records:
            session.add(
                LearnerStack(
                    learner_id=learner.id,
                    stack=stacks[stack_id],
                    started_at=datetime.now(UTC),
                    active=True,
                )
            )
    session.commit()
