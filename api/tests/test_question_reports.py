"""Question Reports are private feedback after recorded answers, never score changes."""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.content.importer import import_folder
from app.db import Base, get_session
from app.models import Question, QuestionReport
from tests.conftest import (
    LEARNER_EMAIL,
    ClientFactory,
    ContentFactory,
    FakeClock,
    complete_lessons,
    onboard,
)
from tests.test_daily_challenge import MC1, MORNING, answered, import_stack
from tests.test_lesson_quiz import start, submit
from tests.test_retakes import answer_retake, pass_missing_one
from tests.test_review import answer_right


def test_after_answer_report_can_be_created_edited_and_read_privately(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content())
    onboard(api)
    complete_lessons(session, "w01-l01")
    url = "/stacks/mini-stack/questions/w01-l01-q01/report"
    assert api.put(url, json={"category": "wrong_answer"}).status_code == 409
    answer_right(api, "w01-l01-q01")
    created = api.put(url, json={"category": "wrong_answer", "note": "Check the premise."})
    assert created.status_code == 200, created.text
    report = created.json()
    assert report["status"] == "open"
    edited = api.put(url, json={"category": "ambiguous_wording", "note": "Two readings."})
    assert edited.status_code == 200
    assert edited.json()["id"] == report["id"]
    reports = api.get("/me/question-reports")
    assert reports.status_code == 200
    assert [(r["category"], r["note"]) for r in reports.json()] == [
        ("ambiguous_wording", "Two readings.")
    ]


@pytest.mark.parametrize(
    "category", ["wrong_answer", "ambiguous_wording", "outdated_claim", "broken_source"]
)
def test_categories_validation_privacy_and_retirement(
    session: Session,
    api: TestClient,
    admin: TestClient,
    signed_in: ClientFactory,
    make_content: ContentFactory,
    category: str,
) -> None:
    import_folder(session, make_content())
    onboard(api)
    complete_lessons(session, "w01-l01")
    answer_right(api, "w01-l01-q01")
    url = "/stacks/mini-stack/questions/w01-l01-q01/report"
    before = api.get("/stacks/mini-stack").json()
    report = api.put(url, json={"category": category}).json()
    assert report["category"] == category
    assert api.get("/stacks/mini-stack").json() == before
    assert api.put(url, json={}).status_code == 422
    assert api.put(url, json={"category": "dispute"}).status_code == 422
    assert api.put(url, json={"category": category, "note": "x" * 4001}).status_code == 422
    admin.post("/invitations", json={"email": "other@example.com"}).raise_for_status()
    other = signed_in("other@example.com")
    onboard(other)
    detail = f"/question-reports/{report['id']}"
    assert other.get(detail).status_code == 404
    assert other.get("/me/question-reports").json() == []
    assert other.get(url).json()["report"] is None
    assert other.put(url, json={"category": category}).status_code == 409
    assert admin.get(detail).status_code == 200
    session.scalars(
        select(Question).where(Question.id == "w01-l01-q01")
    ).one().retired_reason = "The premise is obsolete."
    session.commit()
    assert api.get(url).json()["retired_reason"] == "The premise is obsolete."
    refused = api.put(url, json={"category": category})
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "question_retired"


def test_only_open_reports_can_be_edited_and_final_reports_allow_a_new_report(
    session: Session,
    api: TestClient,
    make_content: ContentFactory,
) -> None:
    import_folder(session, make_content())
    onboard(api)
    complete_lessons(session, "w01-l01")
    answer_right(api, "w01-l01-q01")
    url = "/stacks/mini-stack/questions/w01-l01-q01/report"
    first = api.put(url, json={"category": "broken_source"}).json()
    report = session.get(QuestionReport, first["id"])
    assert report is not None
    report.status = "accepted"
    session.commit()
    assert api.put(url, json={"category": "wrong_answer"}).status_code == 409
    assert api.get(url).json()["report"]["status"] == "accepted"
    report.status = "closed"
    report.explanation = "Already addressed."
    session.commit()
    new = api.put(url, json={"category": "wrong_answer"}).json()
    assert new["id"] != first["id"]
    assert len(api.get("/me/question-reports").json()) == 2


def test_concurrent_report_submissions_create_one_unresolved_report(
    engine: Engine,
    app: FastAPI,
    admin: TestClient,
    api: TestClient,
    make_content: ContentFactory,
) -> None:
    schema = f"report_concurrency_{uuid4().hex}"
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
        _, result = pass_missing_one(api)
        question_id = next(q["id"] for q in result["questions"] if q["correct"])
        together = Barrier(2)

        def submit_report(index: int) -> int:
            together.wait(timeout=10)
            return api.put(
                f"/stacks/mini-stack/questions/{question_id}/report",
                json={"category": "wrong_answer", "note": str(index)},
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(submit_report, range(2)))
        assert responses == [200, 200]
        reports = api.get("/me/question-reports").json()
        assert len(reports) == 1
        assert reports[0]["status"] == "open"
    finally:
        app.dependency_overrides[get_session] = previous
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))


def test_unanswered_quiz_slots_are_not_report_eligible_but_answered_slots_are(
    session: Session,
    api: TestClient,
    make_content: ContentFactory,
) -> None:
    import_folder(session, make_content())
    onboard(api)
    quiz = start(api)
    first, second = quiz["questions"][:2]
    submit(api, quiz, {first["id"]: "a"}).raise_for_status()
    for q, status in ((first, 200), (second, 409)):
        assert (
            api.put(
                f"/stacks/mini-stack/questions/{q['id']}/report", json={"category": "wrong_answer"}
            ).status_code
            == status
        )


def test_report_after_retake_keeps_completion_unchanged(
    session: Session,
    api: TestClient,
    make_content: ContentFactory,
) -> None:
    import_folder(session, make_content())
    onboard(api)
    _, result = pass_missing_one(api)
    retake = result["retakes"][0]
    q = retake["question"]
    response = answer_retake(api, retake, "a" if q["type"] == "multiple_choice" else "right").json()
    assert response["lesson_completed"] is True
    before = api.get("/stacks/mini-stack").json()
    assert (
        api.put(
            f"/stacks/mini-stack/questions/{q['id']}/report", json={"category": "ambiguous_wording"}
        ).status_code
        == 200
    )
    assert api.get("/stacks/mini-stack").json() == before


def test_report_after_challenge_keeps_score_and_streak_unchanged(
    session: Session,
    api: TestClient,
    make_content: ContentFactory,
    clock: FakeClock,
) -> None:
    clock.set(MORNING)
    import_stack(session, make_content)
    onboard(api)
    answered(api, MC1, "a")
    before = api.get("/stacks/mini-stack/challenges/today").json()
    assert (
        api.put(
            f"/stacks/mini-stack/questions/{MC1}/report", json={"category": "outdated_claim"}
        ).status_code
        == 200
    )
    assert api.get("/stacks/mini-stack/challenges/today").json() == before
