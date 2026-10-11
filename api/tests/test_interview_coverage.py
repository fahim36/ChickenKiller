"""The reviewed launch batch is usable on every Stack without exposing private evidence."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from app.content.interviews import read_prompts
from app.models import InterviewContent, InterviewSession
from tests.conftest import (
    ADMIN_EMAIL,
    LEARNER_EMAIL,
    FakeClock,
    TokenFactory,
    complete_lessons,
    onboard,
)

ROOT = Path(__file__).resolve().parents[2] / "content"
STACKS = [
    "android-developer",
    "fullstack-dotnet-developer",
    "full-stack-web-dev",
    "agentic-ai-engineer",
]


def test_launch_batch_eligibility_three_topics_manual_choice_and_private_coverage(
    session: Session, api: TestClient, admin: TestClient, clock: FakeClock, make_token: TokenFactory
) -> None:
    for stack in STACKS:
        path = ROOT / stack / "v2026-10-10"
        import_folder(session, path)
        import_folder(session, path)
    assert session.scalar(select(func.count()).select_from(InterviewContent)) == 16
    api.headers["Authorization"] = f"Bearer {make_token(LEARNER_EMAIL)}"
    admin.headers["Authorization"] = f"Bearer {make_token(ADMIN_EMAIL)}"
    onboard(api, *STACKS)
    for stack in STACKS:
        prompts = read_prompts(ROOT / stack)
        assert len(prompts) == 4
        assert len({p.concept for p in prompts}) == 4
        complete_lessons(session, *(p.lesson for p in prompts), stack_id=stack)
        topics = api.get(f"/stacks/{stack}/interviews/topics").json()["topics"]
        assert {t["concept"] for t in topics} == {p.concept for p in prompts}
        result = api.post(f"/stacks/{stack}/interviews", json={})
        assert result.status_code == 201, result.text
        assert len({p["concept"] for p in result.json()["prompts"]}) == 3
        chosen = [prompts[3].concept, prompts[0].concept, prompts[1].concept]
        manual = api.post(f"/stacks/{stack}/interviews", json={"concepts": chosen})
        assert [p["concept"] for p in manual.json()["prompts"]] == chosen
    assert api.get("/admin/interview-coverage").status_code == 403
    coverage = admin.get("/admin/interview-coverage")
    assert coverage.status_code == 200
    assert len(coverage.json()) == 4
    for item in coverage.json():
        assert item["reviewed_prompts"] == item["covered_concepts"] == 4
        assert not any(p["unresolved"] for p in item["prompts"])
    assert "responses" not in coverage.text and "learner_id" not in coverage.text
    # Removal of a current teaching association is reported, without rewriting private history.
    row = session.scalar(select(InterviewContent))
    assert row is not None
    row.document = {**row.document, "lesson": "removed-lesson"}
    session.flush()
    assert any(
        p["unresolved"] for s in admin.get("/admin/interview-coverage").json() for p in s["prompts"]
    )
    assert session.scalar(select(func.count()).select_from(InterviewSession)) == 8
