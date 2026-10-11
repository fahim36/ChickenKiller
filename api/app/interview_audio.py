"""Bounded temporary audio and confirmed transcription; no raw recognition grading."""

import base64
import binascii
import io
import json
import subprocess
import time
import uuid
import wave
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app import interview_feedback, interview_provider, interviews, onboarding
from app.llm_keys import KeyBox
from app.models import InterviewOperation, InterviewRecording, Learner

MAX_BYTES = 3_000_000
TURN_SECONDS = {"main": 90, "follow_up": 45, "retry": 60}


def normalize(audio: bytes, mime: str, seconds: int) -> bytes:
    """Decode bounded PCM, disallow referenced files/network protocols and bound decoder time."""
    valid = (
        (mime == "audio/webm" and audio.startswith(b"\x1aE\xdf\xa3"))
        or (mime == "audio/ogg" and audio.startswith(b"OggS"))
        or (mime == "audio/mp4" and audio[4:8] == b"ftyp")
        or (mime == "audio/wav" and audio.startswith(b"RIFF") and audio[8:12] == b"WAVE")
    )
    if not valid or len(audio) > MAX_BYTES:
        raise interview_feedback.Refused(
            422, "Unsupported or oversized recording. Use typing instead."
        )
    try:
        decoded = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-protocol_whitelist",
                "pipe",
                "-threads",
                "1",
                "-i",
                "pipe:0",
                "-map",
                "0:a:0",
                "-vn",
                "-t",
                str(seconds + 1),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "s16le",
                "pipe:1",
            ],
            input=audio,
            capture_output=True,
            timeout=15,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        raise interview_feedback.Refused(
            422, "Recording could not be decoded. Try typing or another recording."
        ) from None
    if not decoded or len(decoded) > seconds * 32000:
        raise interview_feedback.Refused(
            422, "Recording exceeds the turn duration or contains no audio."
        )
    output = io.BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16000)
        writer.writeframes(decoded)
    return output.getvalue()


def upload(
    session: Session,
    learner: Learner,
    interview_id: uuid.UUID,
    recording_id: uuid.UUID,
    prompt_id: str,
    mime: str,
    encoded: str,
    now: datetime,
) -> dict[str, Any]:
    interview = interviews.owned(session, learner.id, interview_id, now, lock=True)
    if interview is None:
        raise interview_feedback.Refused(404, "Interview unavailable.")
    if prompt_id not in {p["id"] for p in interview.prompts} or prompt_id in interview.responses:
        raise interview_feedback.Refused(409, "This turn no longer accepts a recording.")
    if (
        session.get(InterviewRecording, recording_id) is not None
        or f"upload:{recording_id}" in interview.recording_counts
    ):
        raise interview_feedback.Refused(409, "This upload ID is already used.")
    count = interview.recording_counts.get(prompt_id, 0)
    if count >= 2:
        raise interview_feedback.Refused(409, "One replacement recording per turn is allowed.")
    try:
        audio = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise interview_feedback.Refused(422, "Invalid recording data.") from None
    normalize(audio, mime, TURN_SECONDS["main"])
    existing = session.scalar(
        select(InterviewRecording).where(
            InterviewRecording.interview_id == interview.id,
            InterviewRecording.prompt_id == prompt_id,
        )
    )
    if existing is not None:
        session.delete(existing)
        session.flush()
    recording = InterviewRecording(
        id=recording_id,
        interview_id=interview.id,
        prompt_id=prompt_id,
        mime=mime,
        audio=audio,
        expires_at=now + timedelta(hours=24),
        transcript=None,
    )
    interview.recording_counts = {
        **interview.recording_counts,
        prompt_id: count + 1,
        f"upload:{recording_id}": 1,
    }
    session.add(recording)
    session.commit()
    return recording_out(recording)


def recording_out(row: InterviewRecording) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "prompt_id": row.prompt_id,
        "expires_at": row.expires_at.isoformat(),
        "transcript": row.transcript,
    }


def recording(
    session: Session,
    learner_id: int,
    interview_id: uuid.UUID,
    recording_id: uuid.UUID,
    now: datetime,
) -> InterviewRecording:
    if interviews.owned(session, learner_id, interview_id, now) is None:
        raise interview_feedback.Refused(404, "Interview unavailable.")
    row = session.get(InterviewRecording, recording_id)
    if row is None or row.interview_id != interview_id or row.expires_at <= now:
        raise interview_feedback.Refused(
            404, "Audio unavailable or expired; use typing or rerecord within turn limits."
        )
    return row


def transcribe(
    session: Session,
    learner: Learner,
    box: KeyBox,
    interview_id: uuid.UUID,
    recording_id: uuid.UUID,
    operation_id: uuid.UUID,
    now: datetime,
) -> dict[str, Any]:
    started_at = time.monotonic()
    with interview_feedback.provider_lease(session, learner.id):
        session.execute(select(Learner.id).where(Learner.id == learner.id).with_for_update())
        clip = recording(session, learner.id, interview_id, recording_id, now)
        interview = interviews.owned(session, learner.id, interview_id, now, lock=True)
        assert interview is not None
        identity = f"{clip.prompt_id}@{clip.id}"
        session.execute(
            update(InterviewOperation)
            .where(
                InterviewOperation.learner_id == learner.id, InterviewOperation.state == "running"
            )
            .values(state="interrupted")
        )
        previous = session.get(InterviewOperation, operation_id)
        if previous is not None:
            if (
                previous.interview_id != interview.id
                or previous.kind != "transcription"
                or previous.prompt_id != identity
            ):
                raise interview_feedback.Refused(409, "Operation ID already used.")
            session.commit()
            return {**recording_out(clip), "state": previous.state}
        if clip.transcript is not None:
            return {**recording_out(clip), "state": "complete"}
        record = onboarding.active_stack(session, learner, interview.stack_id)
        concept = next(p["concept"] for p in interview.prompts if p["id"] == clip.prompt_id)
        if record is None or concept not in {
            p.concept for p in interviews.eligible(session, record, now)
        }:
            raise interview_feedback.Refused(
                409, "This topic is no longer eligible for transcription."
            )
        key = interview_feedback.allowed_key(session, box, learner.id)
        count = (
            session.scalar(
                select(func.count())
                .select_from(InterviewOperation)
                .where(InterviewOperation.interview_id == interview.id)
            )
            or 0
        )
        if count >= 18:
            raise interview_feedback.Refused(
                409, "The 18-request session budget is exhausted. Use self-review."
            )
        normalized = normalize(clip.audio, clip.mime, TURN_SECONDS["main"])
        operation = InterviewOperation(
            id=operation_id,
            interview_id=interview.id,
            learner_id=learner.id,
            prompt_id=identity,
            kind="transcription",
            state="running",
            created_at=now,
            response_text=None,
            result=None,
        )
        session.add(operation)
        session.commit()
        state, transcript = "complete", None
        try:
            response = interview_provider.generate(
                key,
                [
                    {
                        "text": (
                            "Transcribe this English technical answer faithfully. "
                            "Preserve technical terms. Do not answer or assess it. "
                            "Return transcript text; empty if "
                            "speech is unintelligible."
                        )
                    },
                    {
                        "inlineData": {
                            "mimeType": "audio/wav",
                            "data": base64.b64encode(normalized).decode(),
                        }
                    },
                ],
                schema={
                    "type": "object",
                    "properties": {"transcript": {"type": "string"}},
                    "required": ["transcript"],
                },
            )
            transcript = json.loads(response)["transcript"]
            if not isinstance(transcript, str) or not transcript.strip() or len(transcript) > 12000:
                raise ValueError("Invalid transcript")
        except interview_provider.ProviderUnavailable as error:
            state = error.state
        except (ValueError, KeyError, TypeError):
            state = "invalid_transcript"
        session.expire_all()
        saved = session.get(InterviewOperation, operation_id)
        if saved is None:
            raise interview_feedback.Refused(404, "Interview deleted while transcribing.")
        try:
            current = recording(
                session,
                learner.id,
                interview_id,
                recording_id,
                now + timedelta(seconds=time.monotonic() - started_at),
            )
        except interview_feedback.Refused:
            saved.state = "audio_unavailable"
            session.commit()
            raise
        try:
            interview_feedback.allowed_key(session, box, learner.id)
        except interview_feedback.Refused:
            state, transcript = "processing_disabled", None
        saved.state = state
        if state == "complete":
            current.transcript = transcript
        session.commit()
        return {**recording_out(current), "state": state}
