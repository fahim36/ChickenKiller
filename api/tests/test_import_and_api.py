from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from app.content.loader import ContentError
from app.models import Concept, Lesson, Material, Milestone, Question, Stack, Syllabus, Week
from tests.conftest import ContentFactory, onboard

TABLES = (Stack, Syllabus, Week, Lesson, Milestone, Material, Concept, Question)
LESSON = "/stacks/mini-stack/lessons/w01-l01"


def counts(session: Session) -> dict[str, int]:
    return {
        t.__tablename__: session.scalar(select(func.count()).select_from(t)) or 0 for t in TABLES
    }


def test_import_loads_everything(session: Session, make_content: ContentFactory) -> None:
    result = import_folder(session, make_content())

    assert (result.stack_id, result.version, result.status, result.is_current) == (
        "mini-stack",
        "v2026-01-01",
        "imported",
        True,
    )
    assert counts(session) == {
        "stacks": 1,
        "syllabuses": 1,
        "weeks": 1,
        "lessons": 2,
        "milestones": 1,
        "materials": 2,
        "concepts": 4,
        "questions": 8,
    }


def test_import_twice_changes_nothing(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    folder = make_content()
    import_folder(session, folder)
    onboard(api)
    before = counts(session), api.get(LESSON).json()

    again = import_folder(session, folder)

    assert again.status == "unchanged"
    assert (counts(session), api.get(LESSON).json()) == before


def test_changed_content_under_an_imported_version_is_refused(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content())
    onboard(api)

    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["weeks"][0]["lessons"][0]["title"] = "A quietly edited title"

    with pytest.raises(ContentError, match="already imported with different content"):
        import_folder(session, make_content(edit))
    assert api.get(LESSON).json()["title"] == "First lesson"


def test_stating_a_default_is_the_same_content(
    session: Session, make_content: ContentFactory
) -> None:
    """Versions imported before a field with a default existed still import as unchanged."""
    import_folder(session, make_content())

    def explicit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["stack"]["published"] = True

    assert import_folder(session, make_content(explicit)).status == "unchanged"


def test_invalid_content_is_not_imported(session: Session, make_content: ContentFactory) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        bank["questions"][0]["answer"] = "c"

    with pytest.raises(ContentError, match="answer is not one of the choices"):
        import_folder(session, make_content(edit))
    assert counts(session)["syllabuses"] == 0


def test_a_newer_version_becomes_the_current_syllabus(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content())
    onboard(api)

    def newer(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["version"] = "v2026-02-01"
        syllabus["weeks"][0]["lessons"][0]["title"] = "First lesson, revised"

    result = import_folder(session, make_content(newer))

    assert result.is_current
    assert api.get("/stacks/mini-stack").json()["version"] == "v2026-02-01"
    assert api.get(LESSON).json()["title"] == "First lesson, revised"


def test_an_older_version_does_not_replace_the_current_one(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    def newer(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["version"] = "v2026-02-01"

    import_folder(session, make_content(newer))
    onboard(api)
    result = import_folder(session, make_content())

    assert (result.status, result.is_current) == ("imported", False)
    assert api.get("/stacks/mini-stack").json()["version"] == "v2026-02-01"


@pytest.fixture
def client(session: Session, api: TestClient, make_content: ContentFactory) -> Iterator[TestClient]:
    import_folder(session, make_content())
    onboard(api)
    yield api


def test_lesson_page_data(client: TestClient) -> None:
    body = client.get(LESSON).json()
    assert body["title"] == "First lesson"
    assert body["topics"] == ["Topic A", "Topic B"]
    assert [(m["id"], m["type"]) for m in body["materials"]] == [
        ("mat-docs", "docs"),
        ("mat-video", "video"),
    ]
    assert body["week"] == {"id": "w01", "number": 1, "title": "Week one"}
    assert (body["previous_lesson_id"], body["next_lesson_id"]) == (None, "w01-l02")


def test_last_lesson_links_back(client: TestClient) -> None:
    body = client.get("/stacks/mini-stack/lessons/w01-l02").json()
    assert (body["previous_lesson_id"], body["next_lesson_id"]) == ("w01-l01", None)


def test_lesson_does_not_leak_questions(client: TestClient) -> None:
    body = client.get(LESSON).json()
    assert "questions" not in body and "answer" not in str(body)


def test_stack_list(client: TestClient) -> None:
    assert client.get("/stacks").json() == [
        {
            "id": "mini-stack",
            "name": "Mini Stack",
            "summary": "A tiny Stack for tests.",
            "version": "v2026-01-01",
        }
    ]


def test_syllabus_outline(client: TestClient) -> None:
    body = client.get("/stacks/mini-stack").json()
    assert body["name"] == "Mini Stack"
    week = body["weeks"][0]
    assert [lesson["id"] for lesson in week["lessons"]] == ["w01-l01", "w01-l02"]
    assert week["milestones"][0]["kind"] == "build"


@pytest.mark.parametrize(
    "path", ["/stacks/mini-stack/lessons/nope", "/stacks/nope/lessons/w01-l01", "/stacks/nope"]
)
def test_unknown_lesson_or_stack_is_404(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 404
