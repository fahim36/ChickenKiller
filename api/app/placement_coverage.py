"""Admin maintenance coverage and a shared placement eligibility gate."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.placement import PlacementPlan
from app.models import PlacementCoverage, Question, Stack, Week


def gaps(session: Session, plan: PlacementPlan) -> list[str]:
    problems: list[str] = []
    for lesson in plan.lessons:
        questions = list(
            session.scalars(
                select(Question).where(
                    Question.stack_id == plan.stack,
                    Question.id.in_(lesson.questions),
                    Question.retired_reason.is_(None),
                    Question.lesson_id == lesson.lesson,
                    Question.type.in_(["multiple_choice", "multiple_select"]),
                )
            )
        )
        concepts = {q.concept.id for q in questions}
        if len(questions) < lesson.count:
            problems.append(f"{lesson.lesson}: fewer than {lesson.count} suitable Questions")
        for concept in lesson.essential_concepts:
            if concept not in concepts:
                problems.append(f"{lesson.lesson}: no active Question for {concept}")
    return problems


def coverage(session: Session) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for stack in session.scalars(select(Stack).order_by(Stack.id)):
        weeks: list[dict[str, Any]] = []
        for week in session.scalars(
            select(Week)
            .where(Week.syllabus_pk == stack.current_syllabus_pk)
            .order_by(Week.position)
        ):
            row = session.get(PlacementCoverage, (week.syllabus_pk, week.id))
            problems = (
                ["No reviewed placement plan"]
                if row is None
                else gaps(session, PlacementPlan.model_validate(row.document))
            )
            weeks.append(
                {
                    "id": week.id,
                    "title": week.title,
                    "status": "absent" if row is None else "gaps" if problems else "valid",
                    "gaps": problems,
                    "plan": row.document if row else None,
                    "teaching_revision": row.teaching_revision if row else None,
                }
            )
        result.append({"id": stack.id, "name": stack.name, "weeks": weeks})
    return result
