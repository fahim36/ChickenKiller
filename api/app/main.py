from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_session
from app.models import Lesson, Material, Stack

app = FastAPI(title="Learning App API")

SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/stacks", response_model=list[schemas.StackSummary])
def list_stacks(session: SessionDep) -> list[Stack]:
    return list(session.scalars(select(Stack).order_by(Stack.name)))


@app.get("/stacks/{stack_id}", response_model=schemas.SyllabusOut)
def get_syllabus(stack_id: str, session: SessionDep) -> Stack:
    stack = session.get(Stack, stack_id)
    if stack is None:
        raise HTTPException(404, "Stack not found")
    return stack


@app.get("/lessons/{lesson_id}", response_model=schemas.LessonOut)
def get_lesson(lesson_id: str, session: SessionDep) -> schemas.LessonOut:
    lesson = session.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(404, "Lesson not found")

    week = lesson.week
    stack = session.get(Stack, week.stack_id)
    assert stack is not None
    ordered = [x.id for w in stack.weeks for x in w.lessons]
    i = ordered.index(lesson.id)

    found = session.scalars(select(Material).where(Material.id.in_(lesson.material_ids)))
    by_id = {m.id: m for m in found}
    materials = [by_id[mid] for mid in lesson.material_ids if mid in by_id]

    return schemas.LessonOut(
        id=lesson.id,
        stack_id=stack.id,
        week=schemas.WeekRef(id=week.id, number=week.number, title=week.title),
        title=lesson.title,
        topics=lesson.topics,
        exercise=lesson.exercise,
        minutes=lesson.minutes,
        materials=[schemas.MaterialOut.model_validate(m) for m in materials],
        previous_lesson_id=ordered[i - 1] if i > 0 else None,
        next_lesson_id=ordered[i + 1] if i + 1 < len(ordered) else None,
    )
