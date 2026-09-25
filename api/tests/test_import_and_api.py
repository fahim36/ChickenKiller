from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from app.db import get_session
from app.main import app
from app.models import Concept, Lesson, Material, Milestone, Question, Stack, Week
from tests.conftest import ContentFactory

TABLES = (Stack, Week, Lesson, Milestone, Material, Concept, Question)


def counts(session: Session) -> dict[str, int]:
    return {t.__tablename__: session.scalar(select(func.count()).select_from(t)) for t in TABLES}


def test_import_loads_everything(session: Session, make_content: ContentFactory) -> None:
    import_folder(session, make_content())
    assert counts(session) == {
        "stacks": 1,
        "weeks": 1,
        "lessons": 2,
        "milestones": 1,
        "materials": 2,
        "concepts": 4,
        "questions": 8,
    }


def test_import_twice_changes_nothing(session: Session, make_content: ContentFactory) -> None:
    folder = make_content()
    import_folder(session, folder)
    before = counts(session), session.get(Lesson, "w01-l01").topics
    import_folder(session, folder)
    assert (counts(session), session.get(Lesson, "w01-l01").topics) == before


@pytest.fixture
def client(session: Session, make_content: ContentFactory) -> Iterator[TestClient]:
    import_folder(session, make_content())
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_lesson_page_data(client: TestClient) -> None:
    body = client.get("/lessons/w01-l01").json()
    assert body["title"] == "First lesson"
    assert body["topics"] == ["Topic A", "Topic B"]
    assert [(m["id"], m["type"]) for m in body["materials"]] == [
        ("mat-docs", "docs"),
        ("mat-video", "video"),
    ]
    assert body["week"] == {"id": "w01", "number": 1, "title": "Week one"}
    assert (body["previous_lesson_id"], body["next_lesson_id"]) == (None, "w01-l02")


def test_lesson_does_not_leak_questions(client: TestClient) -> None:
    body = client.get("/lessons/w01-l01").json()
    assert "questions" not in body and "answer" not in str(body)


def test_syllabus_outline(client: TestClient) -> None:
    body = client.get("/stacks/mini-stack").json()
    assert body["name"] == "Mini Stack"
    week = body["weeks"][0]
    assert [lesson["id"] for lesson in week["lessons"]] == ["w01-l01", "w01-l02"]
    assert week["milestones"][0]["kind"] == "build"


def test_unknown_lesson_is_404(client: TestClient) -> None:
    assert client.get("/lessons/nope").status_code == 404
