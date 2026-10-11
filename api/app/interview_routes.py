"""Authenticated self-review endpoints; administrative roles confer no private access."""

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app import interview_audio, interview_feedback, interview_turns, interviews
from app.deps import ActiveStackInPath, AdminLearner, CurrentLearner, KeyBoxDep, Now, SessionDep
from app.interview_coverage import coverage
from app.models import InterviewContent, InterviewOperation, InterviewRecording, InterviewSession

router = APIRouter()


@router.get("/me/interview-transcription")
def transcription_path(_: CurrentLearner) -> dict[str, str]:
    """The unverified Whisper gate cannot be enabled by a request or environment flag."""
    return {
        "selected_path": "gemini_audio",
        "whisper_gate": "disabled_unverified",
        "reason": "Representative recording quality and deployment capacity are unverified.",
    }


class SettingsIn(BaseModel):
    enabled: bool
    processing_consent: bool
    free_project_confirmed: bool


class FeedbackIn(BaseModel):
    operation_id: uuid.UUID
    prompt_id: str
    confirmed: bool


class AudioIn(BaseModel):
    recording_id: uuid.UUID
    prompt_id: str
    mime: str = Field(max_length=50)
    data: str = Field(max_length=4_000_000)


class TranscribeIn(BaseModel):
    operation_id: uuid.UUID


class TurnIn(BaseModel):
    parent_id: str
    kind: Literal["follow_up", "retry"]
    follow_up_id: str | None = None


@router.post("/me/interviews/{interview_id}/audio")
def upload_audio(
    interview_id: uuid.UUID, body: AudioIn, learner: CurrentLearner, session: SessionDep, now: Now
) -> dict[str, Any]:
    try:
        return interview_audio.upload(
            session,
            learner,
            interview_id,
            body.recording_id,
            body.prompt_id,
            body.mime,
            body.data,
            now,
        )
    except interview_feedback.Refused as error:
        session.rollback()
        raise HTTPException(error.status, error.message) from None


@router.get("/me/interviews/{interview_id}/audio/{recording_id}")
def playback_audio(
    interview_id: uuid.UUID,
    recording_id: uuid.UUID,
    learner: CurrentLearner,
    session: SessionDep,
    now: Now,
) -> dict[str, str]:
    import base64

    try:
        clip = interview_audio.recording(session, learner.id, interview_id, recording_id, now)
    except interview_feedback.Refused as error:
        raise HTTPException(error.status, error.message) from None
    return {"mime": clip.mime, "data": base64.b64encode(clip.audio).decode()}


@router.delete("/me/interviews/{interview_id}/audio/{recording_id}", status_code=204)
def cancel_audio(
    interview_id: uuid.UUID,
    recording_id: uuid.UUID,
    learner: CurrentLearner,
    session: SessionDep,
    now: Now,
) -> Response:
    try:
        clip = interview_audio.recording(session, learner.id, interview_id, recording_id, now)
    except interview_feedback.Refused as error:
        raise HTTPException(error.status, error.message) from None
    session.delete(clip)
    session.commit()
    return Response(status_code=204)


@router.post("/me/interviews/{interview_id}/audio/{recording_id}/transcribe")
def transcribe_audio(
    interview_id: uuid.UUID,
    recording_id: uuid.UUID,
    body: TranscribeIn,
    learner: CurrentLearner,
    session: SessionDep,
    box: KeyBoxDep,
    now: Now,
) -> dict[str, Any]:
    try:
        return interview_audio.transcribe(
            session, learner, box, interview_id, recording_id, body.operation_id, now
        )
    except interview_feedback.Refused as error:
        session.rollback()
        raise HTTPException(error.status, error.message) from None


@router.get("/me/interview-settings")
def get_settings(learner: CurrentLearner, session: SessionDep) -> dict[str, bool]:
    return interview_feedback.settings(session, learner.id)


@router.put("/me/interview-settings")
def set_settings(body: SettingsIn, learner: CurrentLearner, session: SessionDep) -> dict[str, bool]:
    try:
        return interview_feedback.save_settings(
            session, learner.id, body.enabled, body.processing_consent, body.free_project_confirmed
        )
    except interview_feedback.Refused as error:
        raise HTTPException(error.status, error.message) from None


@router.post("/me/interviews/{interview_id}/feedback")
def feedback(
    interview_id: uuid.UUID,
    body: FeedbackIn,
    learner: CurrentLearner,
    session: SessionDep,
    box: KeyBoxDep,
    now: Now,
) -> dict[str, Any]:
    try:
        return interview_feedback.request_feedback(
            session,
            box,
            learner,
            interview_id,
            body.operation_id,
            body.prompt_id,
            body.confirmed,
            now,
        )
    except interview_feedback.Refused as error:
        session.rollback()
        raise HTTPException(error.status, error.message) from None


@router.get("/admin/interview-coverage")
def admin_coverage(_: AdminLearner, session: SessionDep) -> list[dict[str, Any]]:
    return coverage(session)


class StartIn(BaseModel):
    concepts: list[str] = Field(default_factory=list, max_length=3)


class ResponseIn(BaseModel):
    prompt_id: str
    text: str | None = Field(default=None, max_length=12000)
    recording_id: uuid.UUID | None = None
    confirmed: bool = False


class SessionOut(BaseModel):
    id: uuid.UUID
    stack_id: str
    expires_at: datetime
    prompts: list[dict[str, Any]]
    responses: dict[str, str | None]
    operations: list[dict[str, Any]] = Field(default_factory=list)
    recordings: list[dict[str, Any]] = Field(default_factory=list)
    turns: list[dict[str, Any]] = Field(default_factory=list)


def output(row: InterviewSession, session: SessionDep, now: datetime) -> SessionOut:
    return SessionOut(
        id=row.id,
        stack_id=row.stack_id,
        expires_at=row.expires_at,
        prompts=row.prompts,
        responses=row.responses,
        turns=interview_turns.output(row),
        operations=[
            interview_feedback.operation_out(op)
            for op in session.scalars(
                select(InterviewOperation)
                .where(InterviewOperation.interview_id == row.id)
                .order_by(InterviewOperation.created_at)
            )
        ],
        recordings=[
            interview_audio.recording_out(clip)
            for clip in session.scalars(
                select(InterviewRecording).where(
                    InterviewRecording.interview_id == row.id,
                    InterviewRecording.expires_at > now,
                )
            )
        ],
    )


@router.get("/stacks/{stack_id}/interviews/topics")
def topics(active: ActiveStackInPath, session: SessionDep, now: Now) -> dict[str, Any]:
    available = interviews.eligible(session, active, now)
    fallback = session.scalar(
        select(InterviewContent)
        .where(InterviewContent.stack_id == active.stack_id)
        .order_by(InterviewContent.id)
    )
    return {
        "topics": [{"concept": p.concept, "id": p.id, "scenario": p.scenario} for p in available],
        "lesson_id": fallback.document["lesson"] if fallback else None,
        "message": None
        if available
        else "Study a reviewed topic by completing a Lesson or playing a Daily Challenge first.",
    }


@router.post("/stacks/{stack_id}/interviews", status_code=201)
def start(body: StartIn, active: ActiveStackInPath, session: SessionDep, now: Now) -> SessionOut:
    try:
        row = interviews.start(session, active, now, body.concepts)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    session.commit()
    return output(row, session, now)


@router.get("/me/interviews")
def history(learner: CurrentLearner, session: SessionDep, now: Now) -> list[SessionOut]:
    return [
        output(row, session, now)
        for row in session.scalars(
            select(InterviewSession)
            .where(
                InterviewSession.learner_id == learner.id,
                InterviewSession.expires_at > now,
            )
            .order_by(InterviewSession.created_at.desc())
            .limit(100)
        )
    ]


@router.get("/me/interviews/{interview_id}")
def detail(
    interview_id: uuid.UUID, learner: CurrentLearner, session: SessionDep, now: Now
) -> SessionOut:
    row = interviews.owned(session, learner.id, interview_id, now)
    if row is None:
        raise HTTPException(404, "Interview unavailable.")
    return output(row, session, now)


@router.post("/me/interviews/{interview_id}/responses")
def respond(
    interview_id: uuid.UUID,
    body: ResponseIn,
    learner: CurrentLearner,
    session: SessionDep,
    now: Now,
) -> SessionOut:
    row = interviews.owned(session, learner.id, interview_id, now, lock=True)
    if row is None:
        raise HTTPException(404, "Interview unavailable.")
    try:
        interview_turns.require_accepts(row, body.prompt_id)
    except ValueError as error:
        raise HTTPException(409, str(error)) from None
    if body.recording_id is not None:
        try:
            clip = interview_audio.recording(
                session, learner.id, interview_id, body.recording_id, now
            )
        except interview_feedback.Refused as error:
            raise HTTPException(error.status, error.message) from None
        if clip.prompt_id != body.prompt_id or not body.confirmed:
            raise HTTPException(422, "Confirm or correct the transcript before saving it.")
    for clip in session.scalars(
        select(InterviewRecording).where(
            InterviewRecording.interview_id == row.id,
            InterviewRecording.prompt_id == body.prompt_id,
        )
    ):
        session.delete(clip)
    row.responses = {
        **row.responses,
        body.prompt_id: body.text.strip() if body.text and body.text.strip() else None,
    }
    session.commit()
    return output(row, session, now)


@router.post("/me/interviews/{interview_id}/turns")
def open_optional_turn(
    interview_id: uuid.UUID,
    body: TurnIn,
    learner: CurrentLearner,
    session: SessionDep,
    now: Now,
) -> SessionOut:
    row = interviews.owned(session, learner.id, interview_id, now, lock=True)
    if row is None:
        raise HTTPException(404, "Interview unavailable.")
    try:
        interview_turns.open_turn(session, row, body.parent_id, body.kind, body.follow_up_id)
    except ValueError as error:
        raise HTTPException(409, str(error)) from None
    session.commit()
    return output(row, session, now)


@router.delete("/me/interviews/{interview_id}", status_code=204)
def remove(
    interview_id: uuid.UUID, learner: CurrentLearner, session: SessionDep, now: Now
) -> Response:
    row = interviews.owned(session, learner.id, interview_id, now, lock=True)
    if row is None:
        raise HTTPException(404, "Interview unavailable.")
    session.delete(row)
    session.commit()
    return Response(status_code=204)
