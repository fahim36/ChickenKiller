"""Self-review is private, expiring and separate from quiz progress."""

import json
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import interviews
from app.content.importer import import_folder
from app.models import Answer, Concept, InterviewContent, InterviewSession
from tests.conftest import ContentFactory, FakeClock, complete_lessons, onboard
from tests.test_interview_content import prompt


def test_reviewed_content_import_and_revision_rules(
    session: Session, make_content: ContentFactory
) -> None:
    path = make_content()
    document = prompt()
    bank = json.loads(
        next((path.parent / "question-bank").glob("*.json")).read_text(encoding="utf-8")
    )
    document.update(stack="mini-stack", concept=bank["concepts"][0]["id"])
    folder = path.parent / "interviews"
    folder.mkdir()
    file = folder / "race-condition.json"
    file.write_text(json.dumps(document), encoding="utf-8")
    import_folder(session, path)
    import_folder(session, path)
    assert session.scalar(select(func.count()).select_from(InterviewContent)) == 1
    document["scenario"] = "A revised scenario."
    file.write_text(json.dumps(document), encoding="utf-8")
    import pytest

    with pytest.raises(ValueError, match="higher version"):
        import_folder(session, path)
    document["version"] = 2
    file.write_text(json.dumps(document), encoding="utf-8")
    import_folder(session, path)
    document["concept"] = "unresolved"
    file.write_text(json.dumps(document), encoding="utf-8")
    from app.content.loader import ContentError

    with pytest.raises(ContentError, match="must resolve"):
        import_folder(session, path)


def seed(session: Session, make_content: ContentFactory, api: TestClient) -> None:
    import_folder(session, make_content())
    onboard(api)
    document = prompt()
    concept = session.scalar(select(Concept.id))
    document.update(stack="mini-stack", concept=concept)
    session.add(InterviewContent(stack_id="mini-stack", id="race-condition", document=document))
    session.flush()


def test_self_review_session_history_and_delete(
    session: Session,
    api: TestClient,
    admin: TestClient,
    make_content: ContentFactory,
    clock: FakeClock,
) -> None:
    seed(session, make_content, api)
    assert api.get("/stacks/mini-stack/interviews/topics").json()["topics"] == []
    assert api.post("/stacks/mini-stack/interviews", json={}).status_code == 422
    complete_lessons(session, "w01-l01")
    before = session.scalar(select(func.count()).select_from(Answer))
    result = api.post("/stacks/mini-stack/interviews", json={})
    assert result.status_code == 201, result.text
    row = result.json()
    assert len(row["prompts"]) == 1
    path = "/me/interviews/" + row["id"]
    assert admin.get(path).status_code == 404
    assert admin.delete(path).status_code == 404
    response = api.post(
        path + "/responses",
        json={"prompt_id": "race-condition", "text": "Use a concurrency token."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["responses"]["race-condition"] == "Use a concurrency token."
    assert api.post(path + "/responses", json={"prompt_id": "race-condition"}).status_code == 409
    assert len(api.get("/me/interviews").json()) == 1
    assert session.scalar(select(func.count()).select_from(Answer)) == before
    stored = session.scalar(select(InterviewContent))
    assert stored is not None
    stored.document = {**stored.document, "scenario": "Changed reviewed content", "version": 2}
    session.flush()
    assert api.get(path).json()["prompts"][0]["scenario"] == row["prompts"][0]["scenario"]
    assert api.delete(path).status_code == 204
    assert api.get(path).status_code == 404


def test_expiry_excludes_and_physically_deletes_text(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    seed(session, make_content, api)
    complete_lessons(session, "w01-l01")
    row = api.post("/stacks/mini-stack/interviews", json={}).json()
    path = "/me/interviews/" + row["id"]
    assert api.post(path + "/responses", json={"prompt_id": "race-condition"}).status_code == 200
    stored = session.scalar(select(InterviewSession))
    assert stored is not None
    clock.set(stored.expires_at + timedelta(seconds=1))
    assert api.get(path).status_code == 404
    assert api.get("/me/interviews").json() == []
    interviews.expire(session, stored.expires_at)
    session.flush()
    assert session.scalar(select(func.count()).select_from(InterviewSession)) == 0
