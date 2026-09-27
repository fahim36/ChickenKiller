"""Learners' own LLM keys for grading (app/llm_keys.py) and the NVIDIA grader (app/grading.py).

A key is stored only encrypted and never sent back; grading uses the Learner's key, else the
Admin's, else the server's default, each falling back to the next when it fails."""

import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import llm_keys
from app.grading import (
    NVIDIA_MODEL,
    ChatCompletionsGrader,
    FallbackGrader,
    Grade,
    GradingFailed,
    parse_chat_grade,
)
from app.models import GradingKey, Learner
from tests.conftest import ADMIN_EMAIL, LEARNER_EMAIL, TEST_KEY_SECRET, FakeGrader

KEY = "nvapi-" + "x" * 40 + "WXYZ"
MODEL_ANSWER = {"summary": "S", "key_points": ["one", "two"]}


def learner_row(session: Session, email: str = LEARNER_EMAIL) -> Learner:
    return session.scalars(select(Learner).where(Learner.email == email)).one()


# --- The API ---------------------------------------------------------------------------------


def test_without_a_key_the_server_grades(api: TestClient) -> None:
    grading = api.get("/me/grading").json()

    assert grading == {
        "key": None,
        "grader": "server",
        "keys_enabled": True,
        "default_model": NVIDIA_MODEL,
    }


def test_a_saved_key_is_encrypted_and_never_sent_back(api: TestClient, session: Session) -> None:
    saved = api.put("/me/grading-key", json={"api_key": KEY})

    assert saved.status_code == 200, saved.text
    assert KEY not in saved.text
    assert saved.json()["key"]["key_hint"] == "WXYZ"
    assert saved.json()["key"]["model"] == NVIDIA_MODEL
    assert saved.json()["grader"] == "own_key"
    row = session.get(GradingKey, learner_row(session).id)
    assert row is not None and KEY not in row.key_ciphertext
    assert llm_keys.KeyBox([TEST_KEY_SECRET]).decrypt(row.key_ciphertext) == KEY
    assert KEY not in api.get("/me/grading").text


def test_a_key_can_be_replaced_and_removed(api: TestClient) -> None:
    api.put("/me/grading-key", json={"api_key": KEY}).raise_for_status()
    replaced = api.put("/me/grading-key", json={"api_key": "nvapi-" + "y" * 40, "model": "m/x"})
    assert (replaced.json()["key"]["key_hint"], replaced.json()["key"]["model"]) == ("yyyy", "m/x")

    removed = api.delete("/me/grading-key")

    assert removed.json()["key"] is None
    assert removed.json()["grader"] == "server"


@pytest.mark.parametrize("bad", ["", "short", "has a space in it and is long enough"])
def test_a_key_that_cant_be_right_is_refused(api: TestClient, bad: str) -> None:
    assert api.put("/me/grading-key", json={"api_key": bad}).status_code == 422


def test_a_learner_without_a_key_is_graded_with_the_admins(
    api: TestClient, admin: TestClient
) -> None:
    admin.put("/me/grading-key", json={"api_key": KEY}).raise_for_status()

    assert api.get("/me/grading").json()["grader"] == "admin_key"
    assert api.get("/me/grading").json()["key"] is None


def test_without_a_secret_no_key_can_be_saved(api: TestClient, app: Any) -> None:
    app.state.key_box = llm_keys.KeyBox([])

    assert api.put("/me/grading-key", json={"api_key": KEY}).status_code == 503
    assert api.get("/me/grading").json()["keys_enabled"] is False


# --- Choosing the grader ---------------------------------------------------------------------


def test_the_grader_is_the_learners_key_then_the_admins_then_the_default(
    api: TestClient, admin: TestClient, session: Session
) -> None:
    box, default = llm_keys.KeyBox([TEST_KEY_SECRET]), FakeGrader()
    admins = frozenset({ADMIN_EMAIL})
    api.get("/me").raise_for_status()  # the first request creates the Learner
    me = learner_row(session)

    assert llm_keys.grader_for(session, box, me, admins, default) is default

    admin.put("/me/grading-key", json={"api_key": "nvapi-" + "a" * 40}).raise_for_status()
    chain = llm_keys.grader_for(session, box, me, admins, default)
    assert isinstance(chain, FallbackGrader)
    assert [type(g) for g in chain.graders] == [ChatCompletionsGrader, FakeGrader]

    api.put("/me/grading-key", json={"api_key": KEY}).raise_for_status()
    chain = llm_keys.grader_for(session, box, me, admins, default)
    assert isinstance(chain, FallbackGrader)
    assert len(chain.graders) == 3


def test_a_key_that_cant_be_decrypted_is_skipped(api: TestClient, session: Session) -> None:
    api.put("/me/grading-key", json={"api_key": KEY}).raise_for_status()
    other = llm_keys.KeyBox(["kC3v8VxY4sPq2Dn6Jm1Lr7Tb9Wf0Hg5Ae3Zu8Ki2Oo4="])
    default = FakeGrader()

    assert llm_keys.grader_for(session, other, learner_row(session), frozenset(), default) is (
        default
    )


def test_the_fallback_grader_tries_the_next_when_one_fails() -> None:
    failing, working = FakeGrader(), FakeGrader()
    failing.failing = True

    grade = FallbackGrader([failing, working]).grade("Q?", MODEL_ANSWER, "The right idea.")

    assert grade.passed is True
    assert (len(failing.calls), len(working.calls)) == (1, 1)
    both = FallbackGrader([failing, failing])
    with pytest.raises(GradingFailed):
        both.grade("Q?", MODEL_ANSWER, "x")


# --- The NVIDIA grader -----------------------------------------------------------------------


def nvidia(reply: str | None = None, status: int = 200) -> tuple[ChatCompletionsGrader, list[Any]]:
    requests: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if status != 200:
            return httpx.Response(status, json={"error": "nope"})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": reply}}],
                "usage": {"prompt_tokens": 300, "completion_tokens": 30},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return ChatCompletionsGrader(KEY, client=client), requests


def test_the_nvidia_grader_sends_the_prompt_with_the_key_and_thinking_off() -> None:
    grader, requests = nvidia('{"passed": true, "feedback": "Covers both."}')

    grade = grader.grade("Explain.", MODEL_ANSWER, "The answer.")

    assert grade == Grade(passed=True, feedback="Covers both.")
    [request] = requests
    assert str(request.url) == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert request.headers["authorization"] == f"Bearer {KEY}"
    body = json.loads(request.content)
    assert body["model"] == NVIDIA_MODEL
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert "<learner_answer>\nThe answer.\n</learner_answer>" in body["messages"][1]["content"]


@pytest.mark.parametrize("status", [401, 429, 500])
def test_an_error_from_nvidia_fails_the_grading(status: int) -> None:
    grader, _ = nvidia(status=status)

    with pytest.raises(GradingFailed):
        grader.grade("Explain.", MODEL_ANSWER, "The answer.")


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ('{"passed": false, "feedback": "Misses two."}', Grade(False, "Misses two.")),
        ('```json\n{"passed": true, "feedback": "Good."}\n```', Grade(True, "Good.")),
        (
            '<think>{"passed": false, "feedback": "x"}</think>{"passed": true, "feedback": "Ok."}',
            Grade(True, "Ok."),
        ),
    ],
)
def test_the_grade_is_read_from_the_reply(reply: str, expected: Grade) -> None:
    assert parse_chat_grade(reply) == expected


@pytest.mark.parametrize("reply", ["", "It passes.", '{"passed": "yes", "feedback": "x"}'])
def test_a_reply_without_a_grade_fails(reply: str) -> None:
    with pytest.raises(GradingFailed):
        parse_chat_grade(reply)
