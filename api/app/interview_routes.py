"""Authenticated self-review endpoints; administrative roles confer no private access."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app import interviews
from app.deps import ActiveStackInPath, CurrentLearner, Now, SessionDep
from app.models import InterviewContent, InterviewSession

router = APIRouter()


class StartIn(BaseModel):
    concepts: list[str] = Field(default_factory=list, max_length=3)


class ResponseIn(BaseModel):
    prompt_id: str
    text: str | None = Field(default=None, max_length=12000)


class SessionOut(BaseModel):
    id: uuid.UUID
    stack_id: str
    expires_at: datetime
    prompts: list[dict[str, Any]]
    responses: dict[str, str | None]


def output(row: InterviewSession) -> SessionOut:
    return SessionOut(
        id=row.id,
        stack_id=row.stack_id,
        expires_at=row.expires_at,
        prompts=row.prompts,
        responses=row.responses,
    )


@router.get("/stacks/{stack_id}/interviews/topics")
def topics(active: ActiveStackInPath, session: SessionDep, now: Now) -> dict[str, Any]:
    available = interviews.eligible(session, active, now)
    fallback = session.scalar(
        select(InterviewContent)
        .where(InterviewContent.stack_id == active.stack_id)
        .order_by(InterviewContent.id)
    )
    return {
        "topics": [{"concept": p.concept, "id": p.id, "scenario": p.scenario} for p in available],
        "lesson_id": fallback.document["lesson"] if fallback else None,
        "message": None
        if available
        else "Study a reviewed topic by completing a Lesson or playing a Daily Challenge first.",
    }


@router.post("/stacks/{stack_id}/interviews", status_code=201)
def start(body: StartIn, active: ActiveStackInPath, session: SessionDep, now: Now) -> SessionOut:
    try:
        row = interviews.start(session, active, now, body.concepts)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    session.commit()
    return output(row)


@router.get("/me/interviews")
def history(learner: CurrentLearner, session: SessionDep, now: Now) -> list[SessionOut]:
    return [
        output(row)
        for row in session.scalars(
            select(InterviewSession)
            .where(
                InterviewSession.learner_id == learner.id,
                InterviewSession.expires_at > now,
            )
            .order_by(InterviewSession.created_at.desc())
            .limit(100)
        )
    ]


@router.get("/me/interviews/{interview_id}")
def detail(
    interview_id: uuid.UUID, learner: CurrentLearner, session: SessionDep, now: Now
) -> SessionOut:
    row = interviews.owned(session, learner.id, interview_id, now)
    if row is None:
        raise HTTPException(404, "Interview unavailable.")
    return output(row)


@router.post("/me/interviews/{interview_id}/responses")
def respond(
    interview_id: uuid.UUID,
    body: ResponseIn,
    learner: CurrentLearner,
    session: SessionDep,
    now: Now,
) -> SessionOut:
    row = interviews.owned(session, learner.id, interview_id, now, lock=True)
    if row is None:
        raise HTTPException(404, "Interview unavailable.")
    if body.prompt_id not in {p["id"] for p in row.prompts}:
        raise HTTPException(422, "This scenario is not part of your session.")
    if body.prompt_id in row.responses:
        raise HTTPException(409, "This response is already saved.")
    row.responses = {
        **row.responses,
        body.prompt_id: body.text.strip() if body.text and body.text.strip() else None,
    }
    session.commit()
    return output(row)


@router.delete("/me/interviews/{interview_id}", status_code=204)
def remove(
    interview_id: uuid.UUID, learner: CurrentLearner, session: SessionDep, now: Now
) -> Response:
    row = interviews.owned(session, learner.id, interview_id, now, lock=True)
    if row is None:
        raise HTTPException(404, "Interview unavailable.")
    session.delete(row)
    session.commit()
    return Response(status_code=204)
