"""Reviewed coverage gates placement and is visible only to Admins."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.check import load_checked_folder
from app.content.importer import import_folder
from app.content.loader import ContentError
from app.content.placement import read_plans, teaching_revision
from app.models import PlacementCoverage, Question
from tests.conftest import ContentFactory, make_bank


def fixture_plan(make_content: ContentFactory) -> tuple[Path, dict[str, Any]]:
    second = make_bank("w01-l02", "second", legacy=False)

    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        fresh = make_bank(legacy=False)
        bank.update(fresh)

    path = make_content(edit, extra_banks={"w01-l02": second})
    first = make_bank(legacy=False)
    plan: dict[str, Any] = {
        "stack": "mini-stack",
        "week": "w01",
        "version": 1,
        "reviewed_by": "Test content reviewer",
        "lessons": [
            {
                "lesson": lesson,
                "count": 5,
                "essential_concepts": [c["id"] for c in bank["concepts"]],
                "questions": [q["id"] for q in bank["questions"]],
                "rationale": "Every teaching objective has mapped coverage.",
            }
            for lesson, bank in [("w01-l01", first), ("w01-l02", second)]
        ],
    }
    folder = path / "placement"
    folder.mkdir()
    (folder / "w01.json").write_text(json.dumps(plan), encoding="utf-8")
    return path, plan


def test_import_admin_gate_and_retirement_gap(
    session: Session, api: TestClient, admin: TestClient, make_content: ContentFactory
) -> None:
    assert api.get("/admin/placement-coverage").status_code == 403
    assert admin.get("/admin/placement-coverage").json() == []
    path, _ = fixture_plan(make_content)
    import_folder(session, path)
    import_folder(session, path)
    assert len(list(session.scalars(select(PlacementCoverage)))) == 1
    week = admin.get("/admin/placement-coverage").json()[0]["weeks"][0]
    assert week["status"] == "valid" and week["gaps"] == []
    for q in session.scalars(select(Question).where(Question.lesson_id == "w01-l01")):
        q.retired_reason = "Retired fixture"
    session.flush()
    week = admin.get("/admin/placement-coverage").json()[0]["weeks"][0]
    assert week["status"] == "gaps"
    assert any("fewer than" in gap for gap in week["gaps"])


def test_absent_plan_and_invalid_coverage(
    session: Session, admin: TestClient, make_content: ContentFactory
) -> None:
    path, plan = fixture_plan(make_content)
    plan["lessons"].pop()
    file = path / "placement" / "w01.json"
    file.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(ContentError, match="every Lesson"):
        import_folder(session, path)
    file.unlink()
    import_folder(session, path)
    assert admin.get("/admin/placement-coverage").json()[0]["weeks"][0]["status"] == "absent"


def test_teaching_revision_excludes_question_pool_and_links(make_content: ContentFactory) -> None:
    path, _ = fixture_plan(make_content)
    content = load_checked_folder(path)
    plan = read_plans(content)[0]
    before = teaching_revision(content, plan)
    reduced = plan.model_copy(update={"version": 2, "reviewed_by": "Another reviewer"})
    assert teaching_revision(content, reduced) == before
    content.syllabus.materials[0] = content.syllabus.materials[0].model_copy(
        update={"url": "https://example.com/new-link"}
    )
    assert teaching_revision(content, plan) == before
    content.syllabus.materials[0] = content.syllabus.materials[0].model_copy(
        update={"subject": "Different subject"}
    )
    assert teaching_revision(content, plan) != before
    content.syllabus.materials[0] = content.syllabus.materials[0].model_copy(
        update={"subject": "Python"}
    )
    content.syllabus.weeks[0].lessons[0] = (
        content.syllabus.weeks[0].lessons[0].model_copy(update={"topics": ["Changed teaching"]})
    )
    assert teaching_revision(content, plan) != before


def test_published_plan_cannot_be_overwritten_or_removed(
    session: Session, make_content: ContentFactory
) -> None:
    path, plan = fixture_plan(make_content)
    import_folder(session, path)
    file = path / "placement" / "w01.json"
    plan["version"] = 2
    file.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(ValueError, match="immutable"):
        import_folder(session, path)
    file.unlink()
    with pytest.raises(ValueError, match="cannot be removed"):
        import_folder(session, path)
