from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app import lessons, schemas
from app.db import get_session

SessionDep = Annotated[Session, Depends(get_session)]

# Everything except the health check. Sign-in (#3) is added here as a router dependency.
router = APIRouter()


@router.get("/stacks")
def list_stacks(session: SessionDep) -> list[schemas.StackSummary]:
    return [
        schemas.StackSummary(
            id=s.id, name=s.name, summary=s.summary, version=s.current_syllabus.version
        )
        for s in lessons.list_stacks(session)
        if s.current_syllabus is not None
    ]


@router.get("/stacks/{stack_id}")
def get_syllabus(stack_id: str, session: SessionDep) -> schemas.SyllabusOut:
    syllabus = lessons.current_syllabus(session, stack_id)
    if syllabus is None:
        raise HTTPException(404, "Stack not found")
    stack = syllabus.stack
    return schemas.SyllabusOut(
        id=stack.id,
        name=stack.name,
        summary=stack.summary,
        version=syllabus.version,
        weeks=[schemas.WeekOut.model_validate(week) for week in syllabus.weeks],
    )


@router.get("/stacks/{stack_id}/lessons/{lesson_id}")
def get_lesson(stack_id: str, lesson_id: str, session: SessionDep) -> schemas.LessonOut:
    lesson = lessons.find_current_lesson(session, stack_id, lesson_id)
    if lesson is None:
        raise HTTPException(404, "Lesson not found")
    previous_id, next_id = lessons.neighbour_lesson_ids(session, lesson)
    return schemas.LessonOut(
        id=lesson.id,
        stack_id=stack_id,
        week=schemas.WeekRef.model_validate(lesson.week),
        title=lesson.title,
        topics=lesson.topics,
        exercise=lesson.exercise,
        minutes=lesson.minutes,
        materials=[schemas.MaterialOut.model_validate(m) for m in lesson.materials],
        previous_lesson_id=previous_id,
        next_lesson_id=next_id,
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Learning App API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app


app = create_app()
