"""Building a new Stack (app/stack_builder.py): someone requests it, Claude submits its weekly
plan and then its Questions through the MCP connector, and once the Admin accepts the drafts,
`content-export-drafts` writes a first version that checks and imports."""

import copy
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.content.check import check_stack
from app.content.export_drafts import export_drafts
from app.content.importer import import_folder
from app.models import Stack
from tests.conftest import LEARNER_EMAIL, SYLLABUS, FakeClock, make_bank
from tests.test_mcp_connector import call, mcp, new_token, structured, text  # noqa: F401

NEW = "data-engineer"


def a_request(**changes: Any) -> dict[str, Any]:
    return {
        "id": NEW,
        "name": "Data Engineer",
        "summary": "Pipelines, warehouses and streaming.",
        "audience": "Backend developers moving into data.",
        "weeks": 1,
        **changes,
    }


def a_plan() -> dict[str, Any]:
    plan = copy.deepcopy(SYLLABUS)
    plan["stack"] = {"id": NEW, "name": "Data Engineer", "summary": "Pipelines."}
    return plan


def request_one(api: TestClient) -> dict[str, Any]:
    response = api.post("/stack-requests", json=a_request())
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_a_requested_stack_waits_for_its_weekly_plan(api: TestClient, admin: TestClient) -> None:
    created = request_one(api)

    assert (created["step"], created["requested_by"]) == ("plan", LEARNER_EMAIL)
    [listed] = admin.get("/stack-requests").json()
    assert listed["stack_id"] == NEW and listed["lessons"] == []
    assert "submit_syllabus" in listed["next_step"]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"id": "Data Engineer"}, "lower-case words"),
        ({"id": "new"}, "lower-case words"),
        ({"weeks": 0}, "between 1 and 52"),
        ({"name": "  "}, "name"),
    ],
)
def test_a_bad_request_is_refused(api: TestClient, changes: dict[str, Any], message: str) -> None:
    response = api.post("/stack-requests", json=a_request(**changes))

    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_a_stack_is_requested_once(api: TestClient, admin: TestClient) -> None:
    request_one(api)

    again = admin.post("/stack-requests", json=a_request())

    assert again.status_code == 422 and "already requested" in again.json()["detail"]


def test_the_connector_requests_a_stack_too(api: TestClient, mcp: TestClient) -> None:  # noqa: F811
    token = new_token(api)["token"]

    fields = a_request()
    fields["stack_id"] = fields.pop("id")

    plan = structured(call(mcp, token, "request_stack", **fields))

    assert plan["step"] == "plan"
    assert structured(call(mcp, token, "list_requested_stacks"))[0]["stack_id"] == NEW


def test_questions_come_after_the_weekly_plan_and_are_tagged_to_its_lessons(
    api: TestClient,
    mcp: TestClient,  # noqa: F811
) -> None:
    request_one(api)
    token = new_token(api)["token"]
    bank = make_bank("w01-l01")

    early = call(mcp, token, "submit_questions", stack_id=NEW, **bank_args(bank))
    assert early["isError"] and "weekly plan" in text(early)

    wrong_stack = {**a_plan(), "stack": {**a_plan()["stack"], "id": "other"}}
    refused = call(mcp, token, "submit_syllabus", stack_id=NEW, syllabus=wrong_stack)
    assert refused["isError"] and "not 'data-engineer'" in text(refused)
    unknown = call(mcp, token, "submit_syllabus", stack_id="nobody-asked", syllabus=a_plan())
    assert unknown["isError"]

    draft = structured(call(mcp, token, "submit_syllabus", stack_id=NEW, syllabus=a_plan()))
    assert draft["kind"] == "syllabus"

    stray = make_bank("w09-l01")
    off_plan = call(mcp, token, "submit_questions", stack_id=NEW, **bank_args(stray))
    assert off_plan["isError"] and "No such Lessons" in text(off_plan)

    structured(call(mcp, token, "submit_questions", stack_id=NEW, **bank_args(bank)))
    again = call(mcp, token, "submit_questions", stack_id=NEW, **bank_args(bank))
    assert again["isError"] and "or a draft" in text(again)

    plan = structured(call(mcp, token, "get_stack_plan", stack_id=NEW))
    assert plan["step"] == "questions"
    assert [(lesson["id"], lesson["ready"]) for lesson in plan["lessons"]] == [
        ("w01-l01", True),
        ("w01-l02", False),
    ]
    assert plan["syllabus"]["stack"]["id"] == NEW


def bank_args(bank: dict[str, Any]) -> dict[str, Any]:
    return {"questions": bank["questions"], "concepts": bank["concepts"]}


def test_accepted_drafts_export_as_a_first_version_that_imports(
    api: TestClient,
    admin: TestClient,
    mcp: TestClient,  # noqa: F811
    session: Session,
    tmp_path: Path,
    clock: FakeClock,
) -> None:
    request_one(api)
    token = new_token(api)["token"]
    structured(call(mcp, token, "submit_syllabus", stack_id=NEW, syllabus=a_plan()))
    for lesson, prefix in [("w01-l01", "concept"), ("w01-l02", "other")]:
        bank = make_bank(lesson, prefix)
        structured(call(mcp, token, "submit_questions", stack_id=NEW, **bank_args(bank)))
    [plan] = api.get("/stack-requests").json()
    assert (plan["step"], plan["lessons_ready"]) == ("review", 2)

    for draft in admin.get("/admin/drafts").json():
        decided = admin.put(f"/admin/drafts/{draft['id']}", json={"status": "accepted"})
        assert decided.status_code == 200
    written = export_drafts(session, tmp_path, clock.now)

    stack_dir = tmp_path / NEW
    assert stack_dir / SYLLABUS["version"] / "syllabus.json" in written
    assert len(list((stack_dir / "question-bank").glob("draft-*.json"))) == 2
    assert not (stack_dir / "drafts").exists()
    assert [p for p in check_stack(stack_dir, baseline=None) if p.level == "error"] == []

    import_folder(session, stack_dir / SYLLABUS["version"])
    session.commit()
    assert session.get(Stack, NEW) is not None
    assert api.get("/stack-requests").json() == []
    assert export_drafts(session, tmp_path, clock.now) == []


def test_the_requester_deletes_a_stack_being_built_with_all_its_drafts(
    api: TestClient,
    admin: TestClient,
    mcp: TestClient,  # noqa: F811
    session: Session,
) -> None:
    request_one(api)
    token = new_token(api)["token"]
    structured(call(mcp, token, "submit_syllabus", stack_id=NEW, syllabus=a_plan()))

    assert api.delete(f"/stack-requests/{NEW}").status_code == 204

    assert api.get("/stack-requests").json() == []
    assert admin.get("/admin/drafts").json() == []
    assert api.delete(f"/stack-requests/{NEW}").status_code == 404


def test_only_the_requester_or_the_admin_deletes_a_stack_request(
    api: TestClient,
    admin: TestClient,
    mcp: TestClient,  # noqa: F811
) -> None:
    admin.post("/stack-requests", json=a_request())
    assert api.delete(f"/stack-requests/{NEW}").status_code == 404
    refused = call(mcp, new_token(api)["token"], "delete_stack_request", stack_id=NEW)
    assert refused["isError"] and "that you may delete" in text(refused)

    request_one_more = api.post("/stack-requests", json=a_request(id="platform-engineer"))
    assert request_one_more.status_code == 201
    assert admin.delete("/stack-requests/platform-engineer").status_code == 204
    gone = structured(call(mcp, new_token(admin)["token"], "delete_stack_request", stack_id=NEW))
    assert gone == {"stack_id": NEW, "drafts_deleted": 1}
    assert admin.get("/stack-requests").json() == []
