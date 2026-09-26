"""A Learner's progress on a Stack: Completed Lessons, Milestone ticks, and the Lesson states
that follow from them.

Everything is keyed by the Learner, the Stack and the content's permanent IDs, never by a
Syllabus version's rows, so progress survives a new version (#13).

- Reads take `learner_id` and `stack_id`: a Stack the Learner has never studied simply has no
  progress.
- Writes take the Learner's `LearnerStack` record (the `ActiveStack` dependency gives it), which
  the progress rows belong to.

The lock-state rule itself is `unlocking.lesson_states`; `lesson_states` here feeds it the
Learner's data: their standing against the current Syllabus (`updated_lessons`, #13) and
whether a Pending Review Round exists today (`pending_review_round`, #9). The Week map, the
Lesson page and the Lesson Quiz guard (`deps.UnlockedLesson`) all use it, so a new input to the
rule is added in one place. Reading the rule needs the clock and the Learner's time zone,
because a Review Round becomes pending two hours after it opens and only the current day's
rounds count.
"""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import review, updated_lessons
from app.models import CompletedLesson, LearnerStack, MilestoneTick, ReviewRound
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


def lesson_states(
    session: Session, learner_id: int, stack_id: str, time_zone: str | None, now: datetime
) -> dict[str, LessonState]:
    """Each Lesson of the Stack's current Syllabus with its state for this Learner at `now`, in
    Syllabus order: while a Pending Review Round exists, the Unlocked Lesson is locked too.
    Updated Lessons (#13) come from comparing the current version with the ones the Learner
    completed Lessons in (`updated_lessons`). Empty if the Stack has no current Syllabus.
    `time_zone` is the Learner's (None before onboarding, when there is no Daily Review)."""
    return updated_lessons.lesson_states(
        session,
        learner_id,
        stack_id,
        pending_review_round=pending_review_round(session, learner_id, stack_id, time_zone, now)
        is not None,
    )


def waiting_for_review(
    session: Session, learner_id: int, stack_id: str, time_zone: str | None, now: datetime
) -> str | None:
    """The Lesson (permanent ID) that would be the Unlocked Lesson but is locked by a Pending
    Review Round; None when no round is pending."""
    if pending_review_round(session, learner_id, stack_id, time_zone, now) is None:
        return None
    states = updated_lessons.lesson_states(session, learner_id, stack_id)
    return next((lesson for lesson, state in states.items() if state == "unlocked"), None)


def pending_review_round(
    session: Session, learner_id: int, stack_id: str, time_zone: str | None, now: datetime
) -> ReviewRound | None:
    """The Learner's Pending Review Round on the Stack at `now`, if any: a round of the
    current day (in `time_zone`) that is unfinished two hours after it opened. Rounds of
    earlier days were dropped at the end of their day and never block."""
    if time_zone is None:
        return None
    unfinished = session.scalars(
        select(ReviewRound)
        .where(
            ReviewRound.learner_id == learner_id,
            ReviewRound.stack_id == stack_id,
            ReviewRound.day == review.review_day(time_zone, now),
            ReviewRound.finished_at.is_(None),
        )
        .order_by(ReviewRound.number)
    ).all()
    return next(
        (r for r in unfinished if review.round_state(r.opened_at, None, now) == "pending"), None
    )


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
