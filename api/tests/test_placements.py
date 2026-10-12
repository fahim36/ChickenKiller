"""Whole-Week start/resume is private, fresh, reserved and invalidated safely."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from app.models import (
    PlacementAttempt,
    PlacementCoverage,
    PlacementReservation,
    Question,
    QuestionExposure,
)
from tests.conftest import (
    ContentFactory,
    FakeClock,
    challenge,
    complete_lessons,
    onboard,
    write_challenges,
)
from tests.test_placement_coverage import fixture_plan

ENTRY = "/stacks/mini-stack/weeks/w01/placement"


def seed(session: Session, api: TestClient, make_content: ContentFactory) -> None:
    path, _ = fixture_plan(make_content)
    import_folder(session, path)
    onboard(api)


def test_start_save_resume_abandon_and_owner_isolation(
    session: Session, api: TestClient, admin: TestClient, make_content: ContentFactory
) -> None:
    seed(session, api, make_content)
    assert api.get(ENTRY).json()["available"] is True
    assert session.scalar(select(func.count()).select_from(QuestionExposure)) == 0
    response = api.post(ENTRY)
    assert response.status_code == 201, response.text
    row = response.json()
    assert len(row["questions"]) == 10
    assert all(
        not {"answer", "answers", "explanation", "sources"}.intersection(q)
        for q in row["questions"]
    )
    path = "/me/placements/" + row["id"]
    assert api.post(ENTRY).json()["id"] == row["id"]
    assert api.get(path).json()["questions"] == row["questions"]
    assert admin.get(path).status_code == 404
    assert (
        admin.post(
            path + "/save", json={"question_id": row["questions"][0]["id"], "answer": "a"}
        ).status_code
        == 404
    )
    question = row["questions"][0]
    answer = ["a", "c"] if question["type"] == "multiple_select" else "a"
    saved = api.post(path + "/save", json={"question_id": question["id"], "answer": answer})
    assert saved.status_code == 200
    assert api.get(path).json()["responses"][question["id"]] == answer
    assert (
        api.post(
            path + "/save", json={"question_id": question["id"], "answer": ["bad"]}
        ).status_code
        == 422
    )
    assert api.post("/stacks/mini-stack/lessons/w01-l01/quiz").status_code == 409
    assert len(list(session.scalars(select(PlacementReservation)))) == 10
    assert api.post(path + "/abandon").json()["state"] == "abandoned"
    assert session.scalar(select(func.count()).select_from(PlacementReservation)) == 0
    assert session.scalar(select(func.count()).select_from(QuestionExposure)) == 10
    assert api.get(ENTRY).json()["available"] is False
    assert api.get(path).json()["state"] == "abandoned"
    assert api.post("/stacks/mini-stack/lessons/w01-l01/quiz").status_code == 200


def test_retirement_and_teaching_change_cancel_without_submission(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    seed(session, api, make_content)
    row = api.post(ENTRY).json()
    question = session.scalar(select(Question).where(Question.id == row["questions"][0]["id"]))
    assert question is not None
    question.retired_reason = "Retired"
    session.flush()
    got = api.get("/me/placements/" + row["id"]).json()
    assert got["state"] == "cancelled" and "retired" in got["reason"]
    assert session.scalar(select(func.count()).select_from(PlacementReservation)) == 0
    assert session.scalar(select(PlacementAttempt.submitted_at)) is None


def test_eligibility_does_not_reopen_completed_or_skip_later_weeks(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    seed(session, api, make_content)
    assert api.get("/stacks/mini-stack/weeks/w02/placement").json()["available"] is False
    complete_lessons(session, "w01-l01", "w01-l02")
    assert api.get(ENTRY).json()["available"] is False
    assert api.post(ENTRY).status_code == 409


def test_review_omits_reserved_and_attempt_revision_cancels(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    seed(session, api, make_content)
    complete_lessons(session, "w01-l01")
    row = api.post(ENTRY).json()
    reserved = {q["id"] for q in row["questions"]}
    assert not reserved.intersection(q["id"] for q in api.get("/review").json()["questions"])
    plan = session.scalar(select(PlacementCoverage))
    assert plan is not None
    plan.teaching_revision = "different-revision"
    session.flush()
    got = api.get("/me/placements/" + row["id"]).json()
    assert got["state"] == "cancelled" and "changed" in got["reason"]
    assert session.scalar(select(func.count()).select_from(PlacementReservation)) == 0


def test_frozen_challenge_keeps_its_questions_during_placement(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    clock.set(datetime(2026, 1, 1, 10, tzinfo=UTC))
    path, _ = fixture_plan(make_content)
    write_challenges(path.parent, challenge(1))
    import_folder(session, path)
    onboard(api)
    started = api.post(ENTRY)
    assert started.status_code == 201, started.text
    frozen = {"w01-l01-q01", "w01-l01-q03", "w01-l01-q07"}
    assert not frozen.intersection(q["id"] for q in started.json()["questions"])
    today = api.get("/stacks/mini-stack/challenges/today")
    assert today.status_code == 200, today.text
    assert {q["id"] for q in today.json()["challenge"]["questions"]} == frozen
    assert today.json()["challenge"]["score"] is None
