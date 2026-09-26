"""Reading the current Syllabus of a Stack."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Lesson, LessonMaterial, Milestone, Stack, Syllabus, Week


def list_stacks(session: Session) -> list[Stack]:
    """Published Stacks that have a current Syllabus, by name, with it loaded."""
    return list(
        session.scalars(
            select(Stack)
            .where(Stack.published, Stack.current_syllabus_pk.is_not(None))
            .options(joinedload(Stack.current_syllabus))
            .order_by(Stack.name)
        )
    )


def current_syllabus(session: Session, stack_id: str) -> Syllabus | None:
    """The Stack's current Syllabus with its Weeks, Lessons and Milestones loaded."""
    return session.scalar(
        select(Syllabus)
        .join(Stack, Stack.current_syllabus_pk == Syllabus.pk)
        .where(Stack.id == stack_id)
        .options(
            joinedload(Syllabus.stack),
            selectinload(Syllabus.weeks).selectinload(Week.lessons),
            selectinload(Syllabus.weeks).selectinload(Week.milestones),
        )
    )


def find_current_lesson(session: Session, stack_id: str, lesson_id: str) -> Lesson | None:
    """The Lesson with this permanent ID in the Stack's current Syllabus, with its Week and
    Materials loaded."""
    return session.scalar(
        select(Lesson)
        .join(Stack, Stack.current_syllabus_pk == Lesson.syllabus_pk)
        .where(Stack.id == stack_id, Lesson.id == lesson_id)
        .options(
            joinedload(Lesson.week),
            selectinload(Lesson.material_links).joinedload(LessonMaterial.material),
        )
    )


def find_current_milestone(session: Session, stack_id: str, milestone_id: str) -> Milestone | None:
    """The Milestone with this permanent ID in the Stack's current Syllabus."""
    return session.scalar(
        select(Milestone)
        .join(Stack, Stack.current_syllabus_pk == Milestone.syllabus_pk)
        .where(Stack.id == stack_id, Milestone.id == milestone_id)
    )


def neighbour_lesson_ids(session: Session, lesson: Lesson) -> tuple[str | None, str | None]:
    """Permanent IDs of the Lessons just before and after this one in its Syllabus."""
    rows = session.execute(
        select(Lesson.position, Lesson.id).where(
            Lesson.syllabus_pk == lesson.syllabus_pk,
            Lesson.position.in_([lesson.position - 1, lesson.position + 1]),
        )
    ).all()
    by_position = {position: lesson_id for position, lesson_id in rows}
    return by_position.get(lesson.position - 1), by_position.get(lesson.position + 1)
