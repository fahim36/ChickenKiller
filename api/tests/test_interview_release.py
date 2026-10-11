"""Release flow uses confirmed evidence, reviewed turns and mocked provider inference."""

import base64
import json
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import interview_provider
from app.content.interviews import InterviewPrompt
from app.models import Answer, InterviewRecording, InterviewSession
from tests.conftest import ContentFactory
from tests.test_interview_audio import setup, wav
from tests.test_interview_content import prompt
from tests.test_interview_feedback import KEY, enable


def assessment(text: str, follow_up: str | None) -> dict[str, object]:
    return {
        "criteria": [
            {
                "dimension": dimension,
                "finding": "Explain coordination at the shared store.",
                "quote": text,
            }
            for dimension in ["correctness", "reasoning", "tradeoffs", "explanation"]
        ],
        "uncertainty": "A brief answer cannot establish implementation correctness.",
        "next_steps": ["Review the teaching Lesson and explain a competing update."],
        "follow_up": follow_up,
    }


def test_record_confirm_feedback_followup_retry_resume_delete(
    api: TestClient, admin: TestClient, session: Session, make_content: ContentFactory
) -> None:
    path = setup(api, session, make_content)
    enable(api)
    before = session.scalar(select(func.count()).select_from(Answer))
    events: list[str] = []

    def generate(key: str, parts: list[dict[str, object]], *, schema: dict[str, object]) -> str:
        assert key == KEY
        events.append("transcription" if "inlineData" in parts[-1] else "feedback")
        if events[-1] == "transcription":
            return json.dumps({"transcript": "Use a taken."})
        context = json.loads(str(parts[0]["text"]).split("\n", 1)[1])
        return json.dumps(
            assessment(
                context["learner_response"],
                context["follow_ups"][0]["id"] if context["follow_ups"] else None,
            )
        )

    with patch("app.interview_provider.generate", side_effect=generate):
        main = "race-condition"
        turn_id = main
        for index, kind in enumerate(["main", "follow_up", "retry"]):
            if kind != "main":
                opened = api.post(
                    path + "/turns",
                    json={
                        "parent_id": main,
                        "kind": kind,
                        "follow_up_id": "replicas" if kind == "follow_up" else None,
                    },
                )
                assert opened.status_code == 200, opened.text
                turn_id = opened.json()["turns"][-1]["id"]
            clip = api.post(
                path + "/audio",
                json={
                    "recording_id": str(uuid.uuid4()),
                    "prompt_id": turn_id,
                    "mime": "audio/wav",
                    "data": base64.b64encode(wav()).decode(),
                },
            )
            assert clip.status_code == 200
            audio_path = path + "/audio/" + clip.json()["id"]
            assert api.get(audio_path).status_code == 200
            assert admin.get(audio_path).status_code == 404
            transcribed = api.post(
                audio_path + "/transcribe", json={"operation_id": str(uuid.uuid4())}
            )
            assert transcribed.json()["transcript"] == "Use a taken."
            corrected = f"Use a token and compare the version, turn {index}."
            confirmed = api.post(
                path + "/responses",
                json={
                    "prompt_id": turn_id,
                    "recording_id": clip.json()["id"],
                    "confirmed": True,
                    "text": corrected,
                },
            )
            assert confirmed.status_code == 200
            assert api.get(audio_path).status_code == 404
            request = {"prompt_id": turn_id, "confirmed": True, "operation_id": str(uuid.uuid4())}
            result = api.post(path + "/feedback", json=request)
            assert result.json()["state"] == "complete"
            assert result.json()["feedback"]["criteria"][0]["quote"] == corrected
            assert api.post(path + "/feedback", json=request).json() == result.json()
        history = api.get("/me/interviews").json()[0]
        assert len(history["responses"]) == 3
        assert len(history["operations"]) == 6
        assert api.get(path).json() == history
        assert history["practice_state"] == "available"
        assert api.delete(path).status_code == 204
    assert events == ["transcription", "feedback"] * 3
    assert session.scalar(select(func.count()).select_from(InterviewRecording)) == 0
    assert session.scalar(select(func.count()).select_from(InterviewSession)) == 0
    assert session.scalar(select(func.count()).select_from(Answer)) == before


@pytest.mark.parametrize(
    "response",
    [
        "A lock in this process protects all replicas.",
        "A process-local lock does not protect other replicas.",
        "I would lock it, but I cannot explain the competing update yet.",
        "Use a token, not a taken, and compare the database version.",
    ],
)
def test_reviewed_response_evidence_preserves_mistakes_negation_and_corrections(
    response: str,
) -> None:
    expected = assessment(response, "replicas")
    with patch("app.interview_provider.generate", return_value=json.dumps(expected)) as provider:
        result = interview_provider.feedback(
            KEY, InterviewPrompt.model_validate(prompt()), response
        )
    assert result["criteria"][0]["quote"] == response
    assert result["follow_up"] == "replicas"
    sent = json.loads(provider.call_args.args[1][0]["text"].split("\n", 1)[1])
    assert sent["learner_response"] == response
    assert "readiness" not in result


def test_provider_timeout_is_one_attempt_without_fallback() -> None:
    import httpx

    def timed_out(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Synthetic timeout", request=request)

    transport = httpx.MockTransport(timed_out)
    with patch("app.interview_provider.httpx.HTTPTransport", return_value=transport):
        with pytest.raises(interview_provider.ProviderUnavailable, match="provider_unavailable"):
            interview_provider.generate(KEY, [{"text": "confirmed text"}], schema={})


def test_private_storage_failure_does_not_expose_bound_parameters(
    api: TestClient,
    session: Session,
    make_content: ContentFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    path = setup(api, session, make_content)
    private = "PRIVATE_RESPONSE_MUST_NOT_APPEAR_IN_LOGS"
    failure = IntegrityError(
        "INSERT private evidence", {"response_text": private}, Exception(private)
    )
    with patch.object(session, "commit", side_effect=failure):
        result = api.post(
            path + "/responses", json={"prompt_id": "race-condition", "text": private}
        )
    assert result.status_code == 503
    assert private not in result.text
    assert private not in caplog.text
    invalid = api.post(
        path + "/responses", json={"prompt_id": "race-condition", "text": private * 500}
    )
    assert invalid.status_code == 422
    assert private not in invalid.text
