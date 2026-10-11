"""Only an imported, associated correction can resolve an accepted Question Report."""

from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from app.content.loader import ContentError
from tests.conftest import (
    ContentFactory,
    challenge,
    complete_lessons,
    mc_question,
    onboard,
    write_challenges,
)
from tests.test_daily_challenge import SECOND, import_stack
from tests.test_import_question_bank import retire_q01
from tests.test_review import answer_right


def test_associated_retirement_resolves_after_import_not_acceptance(
    session: Session,
    api: TestClient,
    admin: TestClient,
    make_content: ContentFactory,
) -> None:
    original = make_content()
    import_folder(session, original)
    onboard(api)
    complete_lessons(session, "w01-l01")
    answer_right(api, "w01-l01-q01")
    report = api.put(
        "/stacks/mini-stack/questions/w01-l01-q01/report", json={"category": "outdated_claim"}
    ).json()
    decision = f"/admin/question-reports/{report['id']}"
    admin.put(decision, json={"status": "accepted", "explanation": "Confirmed."}).raise_for_status()
    association = admin.put(f"{decision}/correction", json={"kind": "retirement"})
    assert association.status_code == 200, association.text
    assert association.json()["status"] == "accepted"
    import_folder(session, original)
    session.commit()
    assert api.get(f"/question-reports/{report['id']}").json()["status"] == "accepted"

    def retire(_syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        bank["questions"][0]["retired"] = {"reason": "An obsolete premise."}
        bank["questions"].append(mc_question("w01-l01-q09", "concept-a"))

    correction = make_content(retire)
    import_folder(session, correction)
    session.commit()
    final = api.get(f"/question-reports/{report['id']}").json()
    assert final["status"] == "resolved"
    assert final["resolved_at"] is not None
    assert final["resolution_reason"] == "An obsolete premise."
    import_folder(session, correction)
    session.commit()
    assert api.get(f"/question-reports/{report['id']}").json() == final


def accepted(api: TestClient, admin: TestClient) -> str:
    onboard(api)
    report = api.put(
        "/stacks/mini-stack/questions/w01-l01-q01/report", json={"category": "wrong_answer"}
    )
    report.raise_for_status()
    report_id: str = report.json()["id"]
    admin.put(
        f"/admin/question-reports/{report_id}",
        json={"status": "accepted", "explanation": "Confirmed."},
    ).raise_for_status()
    return report_id


def test_replacement_requires_the_exact_active_imported_question_and_association_is_private(
    session: Session,
    api: TestClient,
    admin: TestClient,
    make_content: ContentFactory,
) -> None:
    import_folder(session, make_content())
    onboard(api)
    complete_lessons(session, "w01-l01")
    answer_right(api, "w01-l01-q01")
    report_id = accepted(api, admin)
    path = f"/admin/question-reports/{report_id}/correction"
    assert api.put(path, json={"kind": "retirement"}).status_code == 403
    assert admin.put(path, json={"kind": "replacement"}).status_code == 422
    assert (
        admin.put(path, json={"kind": "replacement", "replacement_id": "w01-l01-q01"}).status_code
        == 422
    )
    plan = {"kind": "replacement", "replacement_id": "w01-l01-q10"}
    association = admin.put(path, json=plan).json()
    assert admin.put(path, json=plan).json() == association
    import_folder(session, make_content(retire_q01))
    session.commit()
    assert api.get(f"/question-reports/{report_id}").json()["status"] == "accepted"

    def exact(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        retire_q01(syllabus, bank)
        bank["questions"][0]["retired"]["replaced_by"] = "w01-l01-q10"
        bank["questions"].append(mc_question("w01-l01-q10", "concept-a"))

    import_folder(session, make_content(exact))
    session.commit()
    assert api.get(f"/question-reports/{report_id}").json()["status"] == "resolved"
    assert admin.put(path, json=plan).status_code == 409


def test_missing_replacement_or_a_failed_import_cannot_resolve_a_report(
    session: Session,
    api: TestClient,
    admin: TestClient,
    make_content: ContentFactory,
) -> None:
    import_stack(session, make_content)
    onboard(api)
    complete_lessons(session, "w01-l01")
    answer_right(api, "w01-l01-q01")
    report_id = accepted(api, admin)
    admin.put(
        f"/admin/question-reports/{report_id}/correction",
        json={"kind": "replacement", "replacement_id": "w01-l01-q09"},
    ).raise_for_status()

    def missing(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        retire_q01(syllabus, bank)
        bank["questions"].pop()

    with pytest.raises(ContentError):
        import_folder(session, make_content(missing), today=date(2026, 1, 1))
    session.rollback()
    assert api.get(f"/question-reports/{report_id}").json()["status"] == "accepted"
    corrected = make_content(retire_q01)
    write_challenges(
        corrected.parent,
        challenge(1, questions=["w01-l01-q02", "w01-l01-q03", "w01-l01-q07"]),
        challenge(2, questions=SECOND),
    )
    # The valid bank imports first, but the subsequent changed released Challenge refuses
    # this transaction. Its tentative report resolution must roll back with the content.
    with pytest.raises(ContentError):
        import_folder(session, corrected, today=date(2026, 1, 1))
    session.rollback()
    assert api.get(f"/question-reports/{report_id}").json()["status"] == "accepted"
    assert (
        api.get("/stacks/mini-stack/questions/w01-l01-q01/report").json()["retired_reason"] is None
    )
    write_challenges(corrected.parent, challenge(1), challenge(2, questions=SECOND))
    import_folder(session, corrected, today=date(2026, 1, 1))
    session.commit()
    assert api.get(f"/question-reports/{report_id}").json()["status"] == "resolved"
