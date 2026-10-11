"""Recorded answers stay private and ungraded until transcript confirmation."""

import base64
import io
import json
import subprocess
import uuid
import wave
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import interview_audio, interview_feedback, interviews
from app.models import InterviewOperation, InterviewRecording
from tests.conftest import ContentFactory, FakeClock, complete_lessons
from tests.test_interview_feedback import FEEDBACK, enable
from tests.test_interviews import seed


def wav(seconds: float = 1) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16000)
        writer.writeframes(b"\x00\x00" * int(seconds * 16000))
    return output.getvalue()


def setup(api: TestClient, session: Session, make_content: ContentFactory) -> str:
    seed(session, make_content, api)
    complete_lessons(session, "w01-l01")
    return "/me/interviews/" + str(api.post("/stacks/mini-stack/interviews", json={}).json()["id"])


def upload(api: TestClient, path: str) -> dict[str, str]:
    response = api.post(
        path + "/audio",
        json={
            "recording_id": str(uuid.uuid4()),
            "prompt_id": "race-condition",
            "mime": "audio/wav",
            "data": base64.b64encode(wav()).decode(),
        },
    )
    assert response.status_code == 200, response.text
    result: dict[str, str] = response.json()
    return result


def test_record_playback_transcribe_correct_confirm_delete_feedback(
    api: TestClient, admin: TestClient, session: Session, make_content: ContentFactory
) -> None:
    path = setup(api, session, make_content)
    clip = upload(api, path)
    audio_path = path + "/audio/" + clip["id"]
    assert api.get(audio_path).json()["data"] == base64.b64encode(wav()).decode()
    assert admin.get(audio_path).status_code == 404
    assert admin.delete(audio_path).status_code == 404
    request = {"operation_id": str(uuid.uuid4())}
    assert api.post(audio_path + "/transcribe", json=request).status_code == 409
    enable(api)
    with patch(
        "app.interview_provider.generate", return_value=json.dumps({"transcript": "Use a taken."})
    ) as provider:
        transcript = api.post(audio_path + "/transcribe", json=request)
        assert transcript.status_code == 200, transcript.text
        assert transcript.json()["transcript"] == "Use a taken."
        assert api.post(audio_path + "/transcribe", json=request).status_code == 200
        assert provider.call_count == 1
    assert api.get(path).json()["responses"] == {}
    confirmed = {
        "prompt_id": "race-condition",
        "recording_id": clip["id"],
        "text": "Use a token.",
        "confirmed": False,
    }
    assert api.post(path + "/responses", json=confirmed).status_code == 422
    assert api.post(path + "/responses", json={**confirmed, "confirmed": True}).status_code == 200
    assert api.get(audio_path).status_code == 404
    assert session.scalar(select(func.count()).select_from(InterviewRecording)) == 0
    with patch("app.interview_provider.feedback", return_value=FEEDBACK) as provider:
        result = api.post(
            path + "/feedback",
            json={
                "prompt_id": "race-condition",
                "operation_id": str(uuid.uuid4()),
                "confirmed": True,
            },
        )
        assert result.json()["state"] == "complete"
        assert provider.call_args.args[2] == "Use a token."
    assert session.scalar(select(func.count()).select_from(InterviewOperation)) == 2


def test_replacement_duplicate_cancel_and_expiry_bounds(
    api: TestClient, session: Session, make_content: ContentFactory, clock: FakeClock
) -> None:
    path = setup(api, session, make_content)
    first = upload(api, path)
    duplicate = {
        "recording_id": first["id"],
        "prompt_id": "race-condition",
        "mime": "audio/wav",
        "data": base64.b64encode(wav()).decode(),
    }
    assert api.post(path + "/audio", json=duplicate).status_code == 409
    api.delete(path + "/audio/" + first["id"]).raise_for_status()
    assert api.post(path + "/audio", json=duplicate).status_code == 409
    second = upload(api, path)
    third = {**duplicate, "recording_id": str(uuid.uuid4())}
    assert api.post(path + "/audio", json=third).status_code == 409
    clock.advance(hours=24)
    assert api.get(path + "/audio/" + second["id"]).status_code == 404
    interviews.expire(session, clock.now)
    assert session.scalar(select(func.count()).select_from(InterviewRecording)) == 0


@pytest.mark.parametrize("seconds", [45, 60, 90])
def test_decoded_duration_bounds(seconds: int) -> None:
    assert interview_audio.normalize(wav(0.5), "audio/wav", seconds)
    with pytest.raises(interview_feedback.Refused, match="duration"):
        interview_audio.normalize(wav(seconds + 0.2), "audio/wav", seconds)


@pytest.mark.parametrize(
    "mime,format,codec",
    [
        ("audio/webm", "webm", "libopus"),
        ("audio/ogg", "ogg", "libopus"),
        ("audio/mp4", "mp4", "aac"),
    ],
)
def test_supported_browser_container_decodes(mime: str, format: str, codec: str) -> None:
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-c:a", codec]
    if format == "mp4":
        args += ["-movflags", "frag_keyframe+empty_moov"]
    audio = subprocess.run(
        [*args, "-f", format, "pipe:1"], input=wav(), capture_output=True, timeout=15, check=True
    ).stdout
    assert interview_audio.normalize(audio, mime, 90)


def test_unsupported_or_oversized_audio_is_rejected() -> None:
    with pytest.raises(interview_feedback.Refused, match="Unsupported"):
        interview_audio.normalize(b"not audio", "audio/wav", 90)
    with pytest.raises(interview_feedback.Refused, match="oversized"):
        interview_audio.normalize(wav(94), "audio/wav", 90)


def test_discard_during_transcription_does_not_resurrect_audio(
    api: TestClient, session: Session, make_content: ContentFactory
) -> None:
    path = setup(api, session, make_content)
    clip = upload(api, path)
    audio_path = path + "/audio/" + clip["id"]
    enable(api)
    operation_id = uuid.uuid4()

    def discarded(*args: object, **kwargs: object) -> str:
        assert api.delete(audio_path).status_code == 204
        return json.dumps({"transcript": "Use a token."})

    with patch("app.interview_provider.generate", side_effect=discarded):
        assert api.post(
            audio_path + "/transcribe", json={"operation_id": str(operation_id)}
        ).status_code == 404
    assert api.get(audio_path).status_code == 404
    operation = session.get(InterviewOperation, operation_id)
    assert operation is not None and operation.state == "audio_unavailable"
    assert session.scalar(select(func.count()).select_from(InterviewRecording)) == 0
