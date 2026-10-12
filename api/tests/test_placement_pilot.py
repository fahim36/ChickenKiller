"""The shipped Week 1 blueprints draw complete fresh coverage in every Stack."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.content.check import load_checked_folder
from app.content.importer import import_folder
from app.content.placement import read_plans

STACKS = [
    "agentic-ai-engineer",
    "android-developer",
    "full-stack-web-dev",
    "fullstack-dotnet-developer",
]


def test_all_shipped_pilot_plans_import_twice_and_draw_every_essential_concept(
    session: Session, api: TestClient, admin: TestClient
) -> None:
    root = Path(__file__).resolve().parents[2] / "content"
    for stack in STACKS:
        folder = root / stack / "v2026-10-10"
        import_folder(session, folder)
        import_folder(session, folder)
    response = api.put("/me/active-stacks", json={"stack_ids": STACKS})
    assert response.status_code == 200, response.text
    coverage = admin.get("/admin/placement-coverage").json()
    assert {s["id"] for s in coverage} == set(STACKS)
    assert all(
        next(w for w in s["weeks"] if w["id"] == "w01")["status"] == "valid" for s in coverage
    )
    for stack in STACKS:
        plan = read_plans(load_checked_folder(root / stack / "v2026-10-10"))[0]
        result = api.post(f"/stacks/{stack}/weeks/w01/placement")
        assert result.status_code == 201, result.text
        row = result.json()
        assert len(row["questions"]) == 5 * len(plan.lessons)
        for lesson in plan.lessons:
            questions = [q for q in row["questions"] if q["lesson"] == lesson.lesson]
            assert len(questions) == lesson.count
            assert set(lesson.essential_concepts) <= {q["concept"] for q in questions}
        assert api.get(f"/stacks/{stack}/weeks/w02/placement").json()["available"] is False
