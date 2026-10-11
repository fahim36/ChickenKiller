"""Own-key opt-in, immutable evidence and bounded provider attempts."""

import json
import uuid
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import interview_provider
from app.content.interviews import InterviewPrompt
from app.models import InterviewOperation
from tests.conftest import ContentFactory, complete_lessons
from tests.test_interview_content import prompt
from tests.test_interviews import seed

KEY = "gemini-" + "x" * 35
FEEDBACK: dict[str, Any] = {
    "criteria": [
        {"dimension": d, "finding": "Explain the missing coordination detail.", "quote": "token"}
        for d in ["correctness", "reasoning", "tradeoffs", "explanation"]
    ],
    "uncertainty": "A short answer cannot establish implementation detail.",
    "next_steps": ["Discuss a concurrent update example."],
    "follow_up": "replicas",
}
SETTINGS = {"enabled": True, "processing_consent": True, "free_project_confirmed": True}


def setup(api: TestClient, session: Session, make_content: ContentFactory) -> str:
    seed(session, make_content, api)
    complete_lessons(session, "w01-l01")
    row = api.post("/stacks/mini-stack/interviews", json={}).json()
    path = "/me/interviews/" + row["id"]
    api.post(
        path + "/responses", json={"prompt_id": "race-condition", "text": "Use a token."}
    ).raise_for_status()
    return str(path)


def enable(api: TestClient) -> None:
    api.put("/me/grading-key", json={"api_key": KEY}).raise_for_status()
    api.put("/me/interview-settings", json=SETTINGS).raise_for_status()


def body(operation_id: str | None = None) -> dict[str, object]:
    return {
        "operation_id": operation_id or str(uuid.uuid4()),
        "prompt_id": "race-condition",
        "confirmed": True,
    }


def test_consent_own_key_confirmation_idempotency_and_private_history(
    api: TestClient, admin: TestClient, session: Session, make_content: ContentFactory
) -> None:
    path = setup(api, session, make_content)
    admin.put("/me/grading-key", json={"api_key": KEY}).raise_for_status()
    with patch("app.interview_provider.feedback", return_value=FEEDBACK) as provider:
        assert api.post(path + "/feedback", json=body()).status_code == 409
        assert api.put("/me/interview-settings", json=SETTINGS).status_code == 422
        enable(api)
        assert api.post(path + "/feedback", json={**body(), "confirmed": False}).status_code == 422
        request = body()
        result = api.post(path + "/feedback", json=request)
        assert result.status_code == 200, result.text
        assert result.json()["state"] == "complete"
        assert api.post(path + "/feedback", json=request).json() == result.json()
        assert api.post(path + "/feedback", json=body()).json() == result.json()
        assert provider.call_count == 1
        assert provider.call_args.args[0] == KEY
        assert admin.post(path + "/feedback", json=body()).status_code == 404
        assert api.get(path).json()["operations"][0]["feedback"] == FEEDBACK
    operation = session.scalar(select(InterviewOperation))
    assert operation is not None and operation.response_text == "Use a token."
    api.delete(path).raise_for_status()
    assert session.scalar(select(func.count()).select_from(InterviewOperation)) == 0


def test_quota_failures_count_to_eighteen_and_preserve_response(
    api: TestClient, session: Session, make_content: ContentFactory
) -> None:
    path = setup(api, session, make_content)
    enable(api)
    with patch(
        "app.interview_provider.feedback",
        side_effect=interview_provider.ProviderUnavailable("quota_exhausted"),
    ) as provider:
        first = body()
        assert api.post(path + "/feedback", json=first).json()["state"] == "quota_exhausted"
        assert api.post(path + "/feedback", json=first).json()["state"] == "quota_exhausted"
        for _ in range(17):
            assert api.post(path + "/feedback", json=body()).json()["state"] == "quota_exhausted"
        assert provider.call_count == 18
        assert api.post(path + "/feedback", json=body()).status_code == 409
        assert provider.call_count == 18
    assert api.get(path).json()["responses"]["race-condition"] == "Use a token."


def test_inflight_reservation_blocks_other_session_and_key_removal(
    api: TestClient, session: Session, make_content: ContentFactory
) -> None:
    path = setup(api, session, make_content)
    enable(api)
    second = "/me/interviews/" + api.post("/stacks/mini-stack/interviews", json={}).json()["id"]
    api.post(
        second + "/responses", json={"prompt_id": "race-condition", "text": "Another token."}
    ).raise_for_status()

    def overlap(*_: object) -> dict[str, object]:
        assert api.post(second + "/feedback", json=body()).status_code == 409
        api.delete("/me/grading-key").raise_for_status()
        return FEEDBACK

    with patch("app.interview_provider.feedback", side_effect=overlap) as provider:
        result = api.post(path + "/feedback", json=body())
        assert result.json()["state"] == "processing_disabled"
        assert result.json()["feedback"] is None
        assert provider.call_count == 1
    assert api.get("/me/interview-settings").json()["enabled"] is False
    assert api.post(second + "/feedback", json=body()).status_code == 409


@pytest.mark.parametrize("field", ["quote", "follow_up", "dimension"])
def test_provider_rejects_fabricated_evidence_or_unreviewed_selection(field: str) -> None:
    bad = json.loads(json.dumps(FEEDBACK))
    if field == "quote":
        bad["criteria"][0]["quote"] = "fabricated"
    elif field == "dimension":
        bad["criteria"][0]["dimension"] = "reasoning"
    else:
        bad["follow_up"] = "generated-new-question"
    with patch("app.interview_provider.generate", return_value=json.dumps(bad)):
        with pytest.raises(interview_provider.ProviderUnavailable) as error:
            interview_provider.feedback(
                KEY, InterviewPrompt.model_validate(prompt()), "Use a token."
            )
        assert error.value.state == "invalid_feedback"
