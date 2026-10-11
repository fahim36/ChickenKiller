"""Content health is Admin-only maintenance evidence from current imported content."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from app.models import Concept, Question
from tests.conftest import ContentFactory, FakeClock, complete_lessons, onboard
from tests.test_review import answer_right

URL = "/admin/content-health"


def test_health_is_admin_only_and_has_honest_empty_state(
    api: TestClient, admin: TestClient
) -> None:
    assert api.get(URL).status_code == 403
    assert admin.get(URL).json() == []


def test_current_content_coverage_types_and_original_source_dates(
    session: Session,
    api: TestClient,
    admin: TestClient,
    make_content: ContentFactory,
    clock: FakeClock,
) -> None:
    clock.set(datetime(2026, 10, 11, tzinfo=UTC))
    import_folder(session, make_content())
    response = admin.get(URL)
    assert response.status_code == 200, response.text
    [health] = response.json()
    assert health["active_questions"] == 8
    assert health["thin_concepts"] == 4
    assert health["retired_only_concepts"] == health["untested_concepts"] == 0
    assert health["lessons"][0]["multiple_choice"] == 6
    assert health["lessons"][0]["multiple_select"] == 0
    assert health["lessons"][0]["legacy_written"] == 2
    assert health["lessons"][0]["quiz_eligible"] is True
    assert health["sources"][0]["oldest_accessed"] == "2026-01-01"
    assert "answer" not in health["concepts"][0]
    assert health["unresolved_reports"] == 0
    onboard(api)
    complete_lessons(session, "w01-l01")
    answer_right(api, "w01-l01-q01")
    report = api.put(
        "/stacks/mini-stack/questions/w01-l01-q01/report", json={"category": "broken_source"}
    ).json()
    assert admin.get(URL).json()[0]["unresolved_reports"] == 1
    admin.put(
        f"/admin/question-reports/{report['id']}", json={"status": "closed", "explanation": "Works"}
    ).raise_for_status()
    assert admin.get(URL).json()[0]["unresolved_reports"] == 0


def test_retired_only_and_untested_concepts_are_distinct_and_removed_lessons_excluded(
    session: Session, admin: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content())
    for q in session.scalars(
        select(Question).where(Question.id.in_(["w01-l01-q01", "w01-l01-q02"]))
    ):
        q.retired_reason = "Retired"
    session.add(Concept(stack_id="mini-stack", id="uncovered", name="Uncovered"))
    q = session.scalars(select(Question).where(Question.id == "w01-l01-q03")).one()
    q.lesson_id = "removed-lesson"
    session.commit()
    [health] = admin.get(URL).json()
    assert health["active_questions"] == 6
    assert health["retired_questions"] == 2
    assert health["retired_only_concepts"] == health["untested_concepts"] == 1
    assert health["without_current_lesson"] == 1
    assert health["lessons"][0]["active_questions"] == 5
    assert health["lessons"][0]["quiz_eligible"] is False
    states = {c["id"]: c["status"] for c in health["concepts"]}
    assert states["concept-a"] == "retired_only"
    assert states["uncovered"] == "untested"
