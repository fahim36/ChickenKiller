"""Admin report decisions are private, explicit and independent of content publication."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.content.importer import import_folder
from app.db import Base, get_session
from tests.conftest import LEARNER_EMAIL, ClientFactory, ContentFactory, complete_lessons, onboard
from tests.test_retakes import pass_missing_one
from tests.test_review import answer_right


def test_admin_groups_reports_and_decides_with_an_explanation(
    session: Session,
    api: TestClient,
    admin: TestClient,
    make_content: ContentFactory,
) -> None:
    import_folder(session, make_content())
    onboard(api)
    complete_lessons(session, "w01-l01")
    answer_right(api, "w01-l01-q01")
    report = api.put(
        "/stacks/mini-stack/questions/w01-l01-q01/report", json={"category": "wrong_answer"}
    ).json()
    queue = admin.get("/admin/question-reports")
    assert queue.status_code == 200, queue.text
    assert queue.json()[0]["question_id"] == "w01-l01-q01"
    assert queue.json()[0]["reports"][0]["id"] == report["id"]
    decision = f"/admin/question-reports/{report['id']}"
    assert admin.put(decision, json={"status": "accepted", "explanation": "  "}).status_code == 422
    accepted = admin.put(
        decision, json={"status": "accepted", "explanation": "Confirmed, correction needed."}
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"
    assert (
        api.get(f"/question-reports/{report['id']}").json()["explanation"]
        == "Confirmed, correction needed."
    )
    assert (
        api.put(
            "/stacks/mini-stack/questions/w01-l01-q01/report", json={"category": "broken_source"}
        ).status_code
        == 409
    )
    assert (
        admin.put(
            decision, json={"status": "closed", "explanation": "Changed my mind."}
        ).status_code
        == 409
    )
    assert api.get("/admin/question-reports").status_code == 403


def test_grouped_reports_keep_other_reporters_hidden_and_closure_has_no_learning_effect(
    session: Session,
    api: TestClient,
    admin: TestClient,
    signed_in: ClientFactory,
    make_content: ContentFactory,
) -> None:
    import_folder(session, make_content())
    onboard(api)
    complete_lessons(session, "w01-l01")
    answer_right(api, "w01-l01-q01")
    url = "/stacks/mini-stack/questions/w01-l01-q01/report"
    first = api.put(url, json={"category": "wrong_answer", "note": "First reporter."}).json()
    admin.post("/invitations", json={"email": "other@example.com"}).raise_for_status()
    other = signed_in("other@example.com")
    onboard(other)
    complete_lessons(session, "w01-l01", email="other@example.com")
    answer_right(other, "w01-l01-q01")
    second = other.put(
        url, json={"category": "ambiguous_wording", "note": "Second reporter."}
    ).json()
    groups = admin.get("/admin/question-reports").json()
    assert len(groups) == 1
    assert {r["id"] for r in groups[0]["reports"]} == {first["id"], second["id"]}
    assert {r["reporter_email"] for r in groups[0]["reports"]} == {
        LEARNER_EMAIL,
        "other@example.com",
    }
    before = api.get("/stacks/mini-stack").json()
    decision = f"/admin/question-reports/{first['id']}"
    assert (
        api.put(decision, json={"status": "closed", "explanation": "Not allowed."}).status_code
        == 403
    )
    assert (
        admin.put(decision, json={"status": "resolved", "explanation": "Not imported."}).status_code
        == 422
    )
    assert (
        admin.put(
            decision, json={"status": "closed", "explanation": " Declined: premise is correct. "}
        ).status_code
        == 200
    )
    own = api.get("/me/question-reports").json()
    assert len(own) == 1
    assert own[0]["status"] == "closed"
    assert own[0]["explanation"] == "Declined: premise is correct."
    assert "reporter_email" not in own[0]
    assert "Second reporter." not in str(own)
    assert other.get(f"/question-reports/{first['id']}").status_code == 404
    assert other.get("/me/question-reports").json()[0]["status"] == "open"
    assert api.get("/stacks/mini-stack").json() == before
    assert api.get(url).json()["retired_reason"] is None


def test_concurrent_admin_decisions_cannot_overwrite_each_other(
    engine: Engine,
    app: FastAPI,
    admin: TestClient,
    api: TestClient,
    make_content: ContentFactory,
) -> None:
    schema = f"triage_concurrency_{uuid4().hex}"
    isolated = engine.execution_options(schema_translate_map={None: schema})
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    previous = app.dependency_overrides[get_session]

    def request_session() -> Iterator[Session]:
        with Session(isolated, expire_on_commit=False) as current:
            yield current

    try:
        Base.metadata.create_all(isolated)
        app.dependency_overrides[get_session] = request_session
        admin.post("/invitations", json={"email": LEARNER_EMAIL}).raise_for_status()
        with Session(isolated) as seed:
            import_folder(seed, make_content())
            seed.commit()
        onboard(api)
        _, quiz = pass_missing_one(api)
        qid = next(q["id"] for q in quiz["questions"] if q["correct"])
        report = api.put(
            f"/stacks/mini-stack/questions/{qid}/report", json={"category": "wrong_answer"}
        ).json()
        together = Barrier(2)

        def decide(status: str) -> tuple[int, str]:
            together.wait(timeout=10)
            response = admin.put(
                f"/admin/question-reports/{report['id']}",
                json={"status": status, "explanation": f"Decision: {status}."},
            )
            return response.status_code, status

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(decide, ("accepted", "closed")))
        assert sorted(code for code, _ in responses) == [200, 409]
        winner = next(status for code, status in responses if code == 200)
        final = api.get(f"/question-reports/{report['id']}").json()
        assert final["status"] == winner
        assert final["explanation"] == f"Decision: {winner}."
    finally:
        app.dependency_overrides[get_session] = previous
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
