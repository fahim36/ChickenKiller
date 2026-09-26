"""A Learner's progress on a Stack: Completed Lessons, Milestone ticks, and the Lesson states
that follow from them.

Everything is keyed by the Learner, the Stack and the content's permanent IDs, never by a
Syllabus version's rows, so progress survives a new version (#13).

- Reads take `learner_id` and `stack_id`: a Stack the Learner has never studied simply has no
  progress.
- Writes take the Learner's `LearnerStack` record (the `ActiveStackInPath` dependency gives
  it), which the progress rows belong to.

The lock-state rule itself is `unlocking.lesson_states`; `lesson_states` here feeds it the
Learner's data: their Completed Lessons, measured against the current Syllabus
(`updated_lessons`, #13). The Week map, the Lesson page and the Lesson Quiz guard
(`deps.UnlockedLesson`) all use it. Lock states depend on completion only: Milestone ticks and
Review never change them.
"""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import updated_lessons
from app.models import CompletedLesson, LearnerStack, MilestoneTick
from app.unlocking import LessonState


def completed_lesson_ids(session: Session, learner_id: int, stack_id: str) -> set[str]:
    """Permanent IDs of the Learner's Completed Lessons on the Stack, including Lessons a later
    Syllabus version removed."""
    return set(
        session.scalars(
            select(CompletedLesson.lesson_id).where(
                CompletedLesson.learner_id == learner_id, CompletedLesson.stack_id == stack_id
            )
        )
    )


def complete_lesson(
    session: Session, record: LearnerStack, lesson_id: str, now: datetime, version: str
) -> None:
    """Make `lesson_id` (a permanent ID) a Completed Lesson for this Learner on this Stack,
    completed in Syllabus `version` (the Lesson Quiz attempt's pinned version).

    The Lesson Quiz calls this once the Pass Mark is met and every Retake is correct (#6, #8).
    Completing a Lesson twice keeps the first `completed_at` and version.
    """
    session.execute(
        insert(CompletedLesson)
        .values(
            learner_id=record.learner_id,
            stack_id=record.stack_id,
            lesson_id=lesson_id,
            completed_at=now,
            syllabus_version=version,
        )
        .on_conflict_do_nothing()
    )
    session.commit()


def lesson_states(session: Session, learner_id: int, stack_id: str) -> dict[str, LessonState]:
    """Each Lesson of the Stack's current Syllabus with its state for this Learner, in Syllabus
    order. Updated Lessons (#13) come from comparing the current version with the ones the
    Learner completed Lessons in (`updated_lessons`). Empty if the Stack has no current
    Syllabus."""
    return updated_lessons.lesson_states(session, learner_id, stack_id)


def ticked_milestone_ids(session: Session, learner_id: int, stack_id: str) -> set[str]:
    """Permanent IDs of the Milestones the Learner has ticked on the Stack."""
    return set(
        session.scalars(
            select(MilestoneTick.milestone_id).where(
                MilestoneTick.learner_id == learner_id, MilestoneTick.stack_id == stack_id
            )
        )
    )


def set_milestone_ticked(
    session: Session, record: LearnerStack, milestone_id: str, ticked: bool, now: datetime
) -> None:
    """Tick or untick a Milestone (by permanent ID). Doing it twice changes nothing. Ticks are
    the Learner's own record and never affect unlocking."""
    if ticked:
        session.execute(
            insert(MilestoneTick)
            .values(
                learner_id=record.learner_id,
                stack_id=record.stack_id,
                milestone_id=milestone_id,
                ticked_at=now,
            )
            .on_conflict_do_nothing()
        )
    else:
        session.execute(
            delete(MilestoneTick).where(
                MilestoneTick.learner_id == record.learner_id,
                MilestoneTick.stack_id == record.stack_id,
                MilestoneTick.milestone_id == milestone_id,
            )
        )
    session.commit()
