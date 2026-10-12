"""Placement cannot bypass known gaps that already require Retakes."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import ContentFactory
from tests.test_placements import ENTRY, seed


def test_pending_retakes_block_placement_start(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    seed(session, api, make_content)
    quiz = api.post("/stacks/mini-stack/lessons/w01-l01/quiz").json()
    answers = {
        q["id"]: ["a", "c"] if q["type"] == "multiple_select" else "a" for q in quiz["questions"]
    }
    answers[quiz["questions"][0]["id"]] = "b"
    result = api.post(
        "/stacks/mini-stack/lessons/w01-l01/quiz/" + quiz["attempt_id"] + "/answers",
        json={"answers": answers},
    )
    assert result.status_code == 200, result.text
    assert result.json()["passed"] is True
    info = api.get(ENTRY).json()
    assert info["available"] is False and "pending Retakes" in info["reason"]
    assert api.post(ENTRY).status_code == 409
