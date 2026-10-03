"""The MCP connector (app/mcp_server.py) and its personal access tokens (app/access_tokens.py).

A token signs a Claude client in as its Learner; drafts it submits are theirs. Only a hash is
stored, and a revoked token stops working at once."""

import copy
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.export_drafts import export_drafts
from app.content.importer import import_folder
from app.models import AccessToken, ContentDraft
from tests.conftest import (
    LEARNER_EMAIL,
    MS_BANK,
    ContentFactory,
    FakeClock,
)


@pytest.fixture
def mcp(app: FastAPI) -> Iterator[TestClient]:
    """A client that runs the app's lifespan, which the MCP connector needs."""
    with TestClient(app) as client:
        yield client


def call(client: TestClient, token: str | None, tool: str, **arguments: Any) -> Any:
    headers = {"Accept": "application/json, text/event-stream"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        },
    )
    if response.status_code != 200:
        return response
    return response.json()["result"]


def text(result: Any) -> str:
    return " ".join(c.get("text", "") for c in result["content"])


def structured(result: Any) -> Any:
    assert not result.get("isError"), text(result)
    value = result["structuredContent"]
    return value.get("result", value) if isinstance(value, dict) else value


def new_token(client: TestClient, name: str = "Claude Desktop") -> dict[str, Any]:
    response = client.post("/me/access-tokens", json={"name": name})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


# --- Tokens ----------------------------------------------------------------------------------


def test_a_new_token_is_shown_once_and_only_its_hash_is_stored(
    api: TestClient, session: Session
) -> None:
    created = new_token(api)

    assert created["token"].startswith("ica_") and len(created["token"]) > 40
    assert created["prefix"] == created["token"][:10]
    listed = api.get("/me/access-tokens").json()
    assert [t["name"] for t in listed] == ["Claude Desktop"]
    assert "token" not in listed[0]
    stored = session.scalars(select(AccessToken.token_hash)).all()
    assert created["token"] not in stored


def test_a_revoked_token_stops_working(api: TestClient, mcp: TestClient) -> None:
    created = new_token(api)
    assert structured(call(mcp, created["token"], "whoami"))["email"] == LEARNER_EMAIL

    assert api.delete(f"/me/access-tokens/{created['id']}").status_code == 204

    assert call(mcp, created["token"], "whoami").status_code == 401
    assert api.get("/me/access-tokens").json() == []


def test_a_learner_cant_revoke_someone_elses_token(api: TestClient, admin: TestClient) -> None:
    admins = new_token(admin)

    assert api.delete(f"/me/access-tokens/{admins['id']}").status_code == 404


@pytest.mark.parametrize("token", [None, "ica_not-a-real-token", "Bearer-less"])
def test_the_connector_refuses_a_request_without_a_valid_token(
    mcp: TestClient, token: str | None
) -> None:
    response = call(mcp, token, "whoami")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


# --- Tools -----------------------------------------------------------------------------------


@pytest.fixture
def imported(session: Session, make_content: ContentFactory, clock: FakeClock) -> None:
    """The mini Stack, with multiple-select Questions (q07, q08) where it once had written."""

    def multiple_select(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        bank.update(copy.deepcopy(MS_BANK))

    import_folder(session, make_content(multiple_select))


def test_whoami_and_the_stacks(api: TestClient, mcp: TestClient, imported: None) -> None:
    token = new_token(api)["token"]

    assert structured(call(mcp, token, "whoami")) == {"email": LEARNER_EMAIL, "is_admin": False}
    [stack] = structured(call(mcp, token, "list_stacks"))
    syllabus = structured(call(mcp, token, "get_syllabus", stack_id=stack["id"]))
    assert syllabus["weeks"][0]["lessons"][0]["id"] == "w01-l01"


def test_only_the_admin_reads_the_question_bank_and_never_its_answers(
    api: TestClient, admin: TestClient, mcp: TestClient, imported: None
) -> None:
    refused = call(mcp, new_token(api)["token"], "get_question_bank", stack_id="mini-stack")
    assert refused["isError"] and "Only the Admin" in text(refused)

    bank = structured(
        call(mcp, new_token(admin)["token"], "get_question_bank", stack_id="mini-stack")
    )
    assert bank["questions"][0]["id"] == "w01-l01-q01"
    assert all(
        "answer" not in q and "answers" not in q and "model_answer" not in q
        for q in bank["questions"]
    )


def a_question(question_id: str = "w01-l01-q90") -> dict[str, Any]:
    return {
        "id": question_id,
        "lesson": "w01-l01",
        "concept": "concept-a",
        "type": "multiple_choice",
        "prompt": "A new question?",
        "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
        "answer": "a",
        "explanation": "Because.",
        "materials": [],
        "sources": [
            {
                "url": "https://example.com/doc",
                "title": "Doc",
                "publisher": "Example",
                "accessed": "2026-09-27",
                "claim": "It says so.",
            }
        ],
    }


def a_multiple_select_question(question_id: str = "w01-l01-q91") -> dict[str, Any]:
    question = a_question(question_id)
    del question["answer"]
    return question | {
        "type": "multiple_select",
        "prompt": "Which are right? Select all that apply.",
        "choices": [{"id": c, "text": f"Choice {c}"} for c in "abcd"],
        "answers": ["a", "c"],
    }


def a_written_question(question_id: str = "w01-l01-q92") -> dict[str, Any]:
    question = a_question(question_id)
    del question["answer"], question["choices"]
    return question | {
        "type": "written",
        "model_answer": {"summary": "S", "key_points": ["one", "two"]},
    }


def test_a_multiple_select_question_can_be_drafted(
    api: TestClient, admin: TestClient, mcp: TestClient, imported: None
) -> None:
    draft = structured(
        call(
            mcp,
            new_token(api)["token"],
            "submit_questions",
            stack_id="mini-stack",
            questions=[a_multiple_select_question()],
        )
    )

    assert draft["items"] == 1
    [listed] = admin.get("/admin/drafts").json()
    assert listed["payload"]["questions"][0]["answers"] == ["a", "c"]


def test_submitted_questions_are_a_draft_under_the_authors_name(
    api: TestClient, admin: TestClient, mcp: TestClient, imported: None, session: Session
) -> None:
    token = new_token(api)["token"]

    draft = structured(
        call(
            mcp,
            token,
            "submit_questions",
            stack_id="mini-stack",
            questions=[a_question()],
            note="One more on concept a.",
        )
    )

    assert (draft["kind"], draft["status"], draft["items"]) == ("questions", "pending", 1)
    [listed] = admin.get("/admin/drafts").json()
    assert (listed["author_email"], listed["note"]) == (LEARNER_EMAIL, "One more on concept a.")
    assert listed["payload"]["questions"][0]["id"] == "w01-l01-q90"
    assert structured(call(mcp, token, "list_my_drafts"))[0]["id"] == draft["id"]


@pytest.mark.parametrize(
    ("question", "message"),
    [
        (a_question("w01-l01-q01"), "already in the bank"),
        ({**a_question(), "concept": "concept-zz"}, "Unknown Concepts"),
        ({**a_question(), "sources": []}, "isn't valid"),
        (a_written_question(), "Written Questions are no longer accepted"),
        ({**a_multiple_select_question(), "answers": ["a", "e"]}, "'e' is not one of the choices"),
        (
            {**a_multiple_select_question(), "answers": ["a", "b", "c", "d"]},
            "every choice is correct",
        ),
    ],
)
def test_a_bad_question_is_refused(
    api: TestClient, mcp: TestClient, imported: None, question: dict[str, Any], message: str
) -> None:
    result = call(
        mcp,
        new_token(api)["token"],
        "submit_questions",
        stack_id="mini-stack",
        questions=[question],
    )

    assert result["isError"] and message in text(result)


def test_a_challenge_draft_needs_three_live_questions_on_a_free_future_day(
    api: TestClient, mcp: TestClient, imported: None, clock: FakeClock
) -> None:
    token = new_token(api)["token"]
    three = ["w01-l01-q01", "w01-l01-q03", "w01-l01-q07"]
    day = (clock.now.date() + timedelta(days=1)).isoformat()
    past = call(
        mcp, token, "submit_challenge", stack_id="mini-stack", day="2020-01-01", question_ids=three
    )
    assert past["isError"] and "future" in text(past)
    two = call(
        mcp, token, "submit_challenge", stack_id="mini-stack", day=day, question_ids=three[:2]
    )
    assert two["isError"]
    wrong_order = call(
        mcp,
        token,
        "submit_challenge",
        stack_id="mini-stack",
        day=day,
        question_ids=[three[2], three[0], three[1]],
    )
    assert wrong_order["isError"] and "then one multiple select" in text(wrong_order)

    draft = structured(
        call(mcp, token, "submit_challenge", stack_id="mini-stack", day=day, question_ids=three)
    )
    assert draft["kind"] == "challenge"


def test_the_admin_accepts_a_draft_and_the_export_writes_it_once(
    api: TestClient,
    admin: TestClient,
    mcp: TestClient,
    imported: None,
    session: Session,
    tmp_path: Any,
    clock: FakeClock,
) -> None:
    token = new_token(api)["token"]
    draft = structured(
        call(mcp, token, "submit_questions", stack_id="mini-stack", questions=[a_question()])
    )
    assert api.put(f"/admin/drafts/{draft['id']}", json={"status": "accepted"}).status_code == 403

    decided = admin.put(f"/admin/drafts/{draft['id']}", json={"status": "accepted"})
    assert decided.json()["status"] == "accepted"

    [path] = export_drafts(session, tmp_path, clock.now)
    assert path == tmp_path / "mini-stack" / "drafts" / f"{draft['id']}-questions.json"
    assert '"author": "learner@example.com"' in path.read_text(encoding="utf-8")
    assert export_drafts(session, tmp_path, clock.now) == []
    assert session.get(ContentDraft, draft["id"]).status == "exported"  # type: ignore[union-attr]
