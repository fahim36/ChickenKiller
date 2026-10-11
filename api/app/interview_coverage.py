"""Administrative reviewed-content diagnostics without private learner data."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Concept, InterviewContent, Lesson, Question, Stack


def coverage(session: Session) -> list[dict[str, Any]]:
    result = []
    for stack in session.scalars(select(Stack).order_by(Stack.id)):
        concepts = set(session.scalars(select(Concept.id).where(Concept.stack_id == stack.id)))
        lessons = set(
            session.scalars(
                select(Lesson.id).where(Lesson.syllabus_pk == stack.current_syllabus_pk)
            )
        )
        teaching = set(
            session.execute(
                select(Concept.id, Question.lesson_id)
                .join(Question, Question.concept_pk == Concept.pk)
                .where(Question.stack_id == stack.id)
            )
        )
        prompts = []
        for row in session.scalars(
            select(InterviewContent)
            .where(InterviewContent.stack_id == stack.id)
            .order_by(InterviewContent.id)
        ):
            document = row.document
            concept, lesson = document["concept"], document["lesson"]
            prompts.append(
                dict(
                    id=row.id,
                    concept=concept,
                    lesson=lesson,
                    version=document["version"],
                    unresolved=concept not in concepts
                    or lesson not in lessons
                    or (concept, lesson) not in teaching,
                )
            )
        result.append(
            dict(
                id=stack.id,
                name=stack.name,
                prompts=prompts,
                reviewed_prompts=len(prompts),
                covered_concepts=len({p["concept"] for p in prompts}),
                concepts_without_prompts=sorted(concepts - {p["concept"] for p in prompts}),
            )
        )
    return result
