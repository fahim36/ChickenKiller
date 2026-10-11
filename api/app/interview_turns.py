"""Server-derived optional turns; reviewed snapshots stay the source of every rubric."""

import uuid
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.interviews import InterviewPrompt
from app.models import InterviewOperation, InterviewSession

Kind = Literal["main", "follow_up", "retry"]
SECONDS: dict[Kind, int] = {"main": 90, "follow_up": 45, "retry": 60}


def resolve(row: InterviewSession, turn_id: str) -> tuple[InterviewPrompt, Kind]:
    for document in row.prompts:
        if document["id"] == turn_id:
            return InterviewPrompt.model_validate(document), "main"
    turn = row.turns.get(turn_id)
    if turn is None:
        raise ValueError("This turn is not part of your session.")
    parent = next(p for p in row.prompts if p["id"] == turn["parent_id"])
    prompt = InterviewPrompt.model_validate(parent)
    if turn["kind"] == "retry":
        return prompt.model_copy(update={"id": turn_id, "follow_ups": []}), "retry"
    follow_up = next(f for f in prompt.follow_ups if f.id == turn["follow_up_id"])
    return prompt.model_copy(
        update={
            "id": turn_id,
            "scenario": follow_up.scenario,
            "rubric": follow_up.rubric,
            "follow_ups": [],
        }
    ), "follow_up"


def require_accepts(row: InterviewSession, turn_id: str) -> tuple[InterviewPrompt, Kind]:
    prompt, kind = resolve(row, turn_id)
    if turn_id in row.responses:
        raise ValueError("This response is already saved.")
    if len(row.responses) >= 9:
        raise ValueError("The nine-response session limit is reached.")
    pending = next((key for key in row.turns if key not in row.responses), None)
    if pending is not None and pending != turn_id:
        raise ValueError("Finish or skip the open optional turn first.")
    if kind == "main":
        expected = next((p["id"] for p in row.prompts if p["id"] not in row.responses), None)
        if expected != turn_id:
            raise ValueError("Answer or skip scenarios in their session order.")
    return prompt, kind


def open_turn(
    session: Session,
    row: InterviewSession,
    parent_id: str,
    kind: Literal["follow_up", "retry"],
    follow_up_id: str | None,
) -> None:
    parent, parent_kind = resolve(row, parent_id)
    if parent_kind != "main" or not row.responses.get(parent_id):
        raise ValueError("Save a main response before optional practice.")
    if any(key not in row.responses for key in row.turns):
        raise ValueError("Finish or skip the open optional turn first.")
    siblings = [t for t in row.turns.values() if t["parent_id"] == parent_id]
    if any(t["kind"] == kind for t in siblings):
        raise ValueError("Only one follow-up and one practice retry per scenario are allowed.")
    if kind == "follow_up":
        if any(t["kind"] == "retry" for t in siblings):
            raise ValueError("Follow-ups must come before the practice retry.")
        if follow_up_id not in {f.id for f in parent.follow_ups}:
            raise ValueError("Choose a reviewed follow-up from this scenario.")
        if session.scalar(
            select(InterviewOperation.id).where(
                InterviewOperation.interview_id == row.id,
                InterviewOperation.prompt_id == parent_id,
                InterviewOperation.kind == "feedback",
                InterviewOperation.state == "running",
            )
        ):
            raise ValueError("Wait for the current feedback before choosing a follow-up.")
        feedback = session.scalar(
            select(InterviewOperation).where(
                InterviewOperation.interview_id == row.id,
                InterviewOperation.prompt_id == parent_id,
                InterviewOperation.kind == "feedback",
                InterviewOperation.state == "complete",
            )
        )
        if feedback is not None and (
            feedback.result is None or feedback.result.get("follow_up") != follow_up_id
        ):
            raise ValueError("Use only the reviewed follow-up selected in saved AI feedback.")
    elif follow_up_id is not None:
        raise ValueError("A practice retry reuses the main scenario.")
    row.turns = {
        **row.turns,
        str(uuid.uuid4()): {
            "parent_id": parent_id,
            "kind": kind,
            "follow_up_id": follow_up_id or "",
        },
    }


def output(row: InterviewSession) -> list[dict[str, Any]]:
    result = []
    for key, turn in row.turns.items():
        prompt, kind = resolve(row, key)
        result.append(
            {
                **prompt.model_dump(),
                "id": key,
                "parent_id": turn["parent_id"],
                "kind": kind,
                "seconds": SECONDS[kind],
            }
        )
    return result
