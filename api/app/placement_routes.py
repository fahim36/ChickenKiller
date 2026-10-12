"""Admin coverage and owner-only saved Placement Quiz endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import placements
from app.deps import ActiveStackInPath, AdminLearner, CurrentLearner, Now, QuizRandom, SessionDep
from app.placement_coverage import coverage

router = APIRouter()


@router.get("/admin/placement-coverage")
def admin_coverage(admin: AdminLearner, session: SessionDep) -> list[dict[str, Any]]:
    return coverage(session)


@router.get("/stacks/{stack_id}/weeks/{week_id}/placement")
def eligibility(week_id: str, active: ActiveStackInPath, session: SessionDep) -> dict[str, Any]:
    info = placements.eligibility(session, active, week_id)
    session.commit()
    return info


@router.post("/stacks/{stack_id}/weeks/{week_id}/placement", status_code=201)
def start(
    week_id: str, active: ActiveStackInPath, session: SessionDep, now: Now, rng: QuizRandom
) -> dict[str, Any]:
    return placements.output(session, placements.start(session, active, week_id, now, rng), now)


@router.get("/me/placements/{attempt_id}")
def get(
    attempt_id: uuid.UUID, learner: CurrentLearner, session: SessionDep, now: Now
) -> dict[str, Any]:
    return placements.output(session, placements.owned(session, learner.id, attempt_id), now)


class SaveIn(BaseModel):
    question_id: str = Field(max_length=80)
    answer: list[str] | str | None


@router.post("/me/placements/{attempt_id}/save")
def save(
    attempt_id: uuid.UUID, body: SaveIn, learner: CurrentLearner, session: SessionDep, now: Now
) -> dict[str, Any]:
    from fastapi import HTTPException

    row = placements.owned(session, learner.id, attempt_id)
    if row.state != "open":
        return placements.output(session, row, now)
    question = next((q for q in row.questions if q["id"] == body.question_id), None)
    if question is None:
        raise HTTPException(422, "Not a Question in this Placement Quiz")
    options = {choice["id"] for choice in question["choices"]}
    values = (
        body.answer
        if isinstance(body.answer, list)
        else []
        if body.answer is None
        else [body.answer]
    )
    if (
        len(values) != len(set(values))
        or not set(values).issubset(options)
        or (question["type"] == "multiple_choice" and len(values) > 1)
    ):
        raise HTTPException(422, "Choose only this Question's options")
    row.responses = {**row.responses, body.question_id: body.answer}
    session.commit()
    return placements.output(session, row, now)


@router.post("/me/placements/{attempt_id}/abandon")
def abandon(
    attempt_id: uuid.UUID, learner: CurrentLearner, session: SessionDep, now: Now
) -> dict[str, Any]:
    row = placements.owned(session, learner.id, attempt_id)
    if row.state == "open":
        placements.release(
            session, row, "abandoned", "You abandoned this attempt. Viewed Questions remain seen."
        )
    return placements.output(session, row, now)
