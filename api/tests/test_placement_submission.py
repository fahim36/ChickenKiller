"""Placement submission is immutable, atomic, exact-match and distinct from Daily scores."""

import json
import shutil
import uuid
from copy import deepcopy

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from app.models import (
    Answer,
    CompletedLesson,
    MilestoneTick,
    PlacementAttempt,
    PlacementReservation,
    Retake,
)
from tests.conftest import (
    ContentFactory,
    changelog_entry,
    complete_lessons,
    make_changelog,
    onboard,
)
from tests.test_placement_coverage import fixture_plan
from tests.test_placements import ENTRY, seed


def test_failed_attempt_can_restart_after_actual_teaching_import(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    old, plan = fixture_plan(make_content)
    for lesson in plan["lessons"]:
        file = old.parent / "question-bank" / (lesson["lesson"] + ".json")
        bank = json.loads(file.read_text())
        extra = deepcopy(bank["questions"])
        for index, q in enumerate(extra, start=9):
            q["id"] = lesson["lesson"] + f"-q{index:02}"
            q["prompt"] += " New fixture variant."
        bank["questions"].extend(extra)
        file.write_text(json.dumps(bank), encoding="utf-8")
        lesson["questions"].extend(q["id"] for q in extra)
    (old / "placement" / "w01.json").write_text(json.dumps(plan), encoding="utf-8")
    import_folder(session, old)
    onboard(api)
    row = api.post(ENTRY).json()
    assert api.post("/me/placements/" + row["id"] + "/submit").json()["result"]["passed"] is False
    assert api.get(ENTRY).json()["available"] is False
    new = old.parent / "v2026-01-02.1"
    shutil.copytree(old, new)
    doc = json.loads((new / "syllabus.json").read_text())
    doc["version"] = new.name
    doc["weeks"][0]["lessons"][0]["topics"] = ["Changed teaching"]
    (new / "syllabus.json").write_text(json.dumps(doc), encoding="utf-8")
    (new / "changelog.json").write_text(
        json.dumps(
            make_changelog(new.name, old.name, changelog_entry("lesson", "w01-l01", "changed"))
        ),
        encoding="utf-8",
    )
    import_folder(session, new)
    session.commit()
    assert api.get(ENTRY).json()["available"] is True
    restarted = api.post(ENTRY).json()
    assert restarted["id"] != row["id"]
    assert not {q["id"] for q in row["questions"]}.intersection(
        q["id"] for q in restarted["questions"]
    )


def fill(session: Session, api: TestClient, row: dict, misses: set[int]) -> str:
    path = "/me/placements/" + row["id"]
    private = session.get_one(PlacementAttempt, uuid.UUID(row["id"]))
    for index, question in enumerate(private.questions):
        if index in misses:
            continue
        response = (
            question["answers"] if question["type"] == "multiple_select" else question["answer"]
        )
        assert (
            api.post(
                path + "/save", json={"question_id": question["id"], "answer": response}
            ).status_code
            == 200
        )
    return path


def test_passing_preserves_completion_and_duplicate_submission(
    session: Session, api: TestClient, admin: TestClient, make_content: ContentFactory
) -> None:
    seed(session, api, make_content)
    complete_lessons(session, "w01-l01")
    before = session.scalar(select(CompletedLesson).where(CompletedLesson.lesson_id == "w01-l01"))
    assert before is not None
    original = (before.completed_at, before.syllabus_version)
    row = api.post(ENTRY).json()
    path = fill(session, api, row, {0, 5})
    result = api.post(path + "/submit").json()
    assert result["result"]["passed"] is True
    assert result["result"]["correct"] == 8
    assert all(score["correct"] == 4 for score in result["result"]["lessons"])
    assert all("sources" in q and "explanation" in q for q in result["questions"])
    assert api.post(path + "/submit").json() == result
    assert (
        api.post(
            path + "/save", json={"question_id": row["questions"][0]["id"], "answer": "a"}
        ).json()
        == result
    )
    assert admin.get(path).status_code == 404
    session.expire_all()
    completions = list(session.scalars(select(CompletedLesson)))
    assert len(completions) == 2
    assert (before.completed_at, before.syllabus_version) == original
    assert before.placement_attempt_id is None
    assert next(
        c for c in completions if c.lesson_id == "w01-l02"
    ).placement_attempt_id == uuid.UUID(row["id"])
    assert (
        session.scalar(
            select(func.count()).select_from(Answer).where(Answer.context == "placement")
        )
        == 10
    )
    assert session.scalar(select(func.count()).select_from(Retake)) == 0
    assert session.scalar(select(func.count()).select_from(MilestoneTick)) == 0
    assert session.scalar(select(func.count()).select_from(PlacementReservation)) == 0
    assert api.get(ENTRY).json()["available"] is False


def test_overall_eighty_does_not_hide_lesson_failure_and_misses_enter_review(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    seed(session, api, make_content)
    row = api.post(ENTRY).json()
    path = fill(session, api, row, {0, 1})
    result = api.post(path + "/submit").json()["result"]
    assert result["correct"] == 8 and result["passed"] is False
    assert session.scalar(select(func.count()).select_from(CompletedLesson)) == 0
    assert session.scalar(select(func.count()).select_from(Retake)) == 0
    misses = set(session.scalars(select(Answer.question_id).where(Answer.correct.is_(False))))
    assert misses == {row["questions"][0]["id"], row["questions"][1]["id"]}
    assert "already submitted" in api.get(ENTRY).json()["reason"]
    reviewed = {q["id"] for q in api.get("/review").json()["questions"]}
    assert misses <= reviewed


def test_multiple_select_partial_answer_is_wrong_and_revision_resets_only_incomplete_week(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    from app.models import PlacementCoverage

    seed(session, api, make_content)
    row = api.post(ENTRY).json()
    path = fill(session, api, row, set())
    private = session.get_one(PlacementAttempt, uuid.UUID(row["id"]))
    multiple = next(q for q in private.questions if q["type"] == "multiple_select")
    api.post(
        path + "/save", json={"question_id": multiple["id"], "answer": multiple["answers"][:1]}
    ).raise_for_status()
    result = api.post(path + "/submit").json()["result"]
    assert result["correct_questions"][multiple["id"]] is False
    assert result["correct"] == 9 and result["passed"] is True
    plan = session.scalar(select(PlacementCoverage))
    assert plan is not None
    plan.teaching_revision = "new-teaching"
    session.flush()
    assert api.get(ENTRY).json()["available"] is False


def test_retired_draw_cancels_submission(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    from app.models import Question

    seed(session, api, make_content)
    row = api.post(ENTRY).json()
    path = fill(session, api, row, set())
    question = session.scalar(select(Question).where(Question.id == row["questions"][0]["id"]))
    assert question is not None
    question.retired_reason = "Withdrawn"
    session.flush()
    assert api.post(path + "/submit").json()["state"] == "cancelled"
    assert session.scalar(select(func.count()).select_from(Answer)) == 0
    assert session.scalar(select(func.count()).select_from(CompletedLesson)) == 0
