"""Consent-gated operations with durable reservations and owner-only result storage."""

import hashlib
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app import interview_provider, interviews, onboarding
from app.content.interviews import InterviewPrompt
from app.grading import GEMINI_BASE_URL
from app.llm_keys import KeyBox
from app.models import GradingKey, InterviewOperation, InterviewSettings, Learner


class Refused(Exception):
    def __init__(self, status: int, message: str) -> None:
        self.status, self.message = status, message


def fingerprint(key: GradingKey) -> str:
    return hashlib.sha256(key.key_ciphertext.encode()).hexdigest()


def settings(session: Session, learner_id: int) -> dict[str, bool]:
    row = session.get(InterviewSettings, learner_id)
    key = session.get(GradingKey, learner_id)
    valid = row is not None and key is not None and row.key_fingerprint == fingerprint(key)
    return dict(
        enabled=bool(valid and row and row.enabled),
        processing_consent=bool(row and row.processing_consent),
        free_project_confirmed=bool(valid and row and row.free_project_confirmed),
    )


def save_settings(
    session: Session, learner_id: int, enabled: bool, consent: bool, free: bool
) -> dict[str, bool]:
    enabled = enabled and consent and free
    key = session.get(GradingKey, learner_id)
    if enabled and (
        not consent
        or not free
        or key is None
        or key.provider != "gemini"
        or key.base_url != GEMINI_BASE_URL
    ):
        raise Refused(
            422,
            "Save your own Gemini key and confirm free-project use and processing consent first.",
        )
    row = session.get(InterviewSettings, learner_id)
    if row is None:
        row = InterviewSettings(learner_id=learner_id)
        session.add(row)
    row.enabled, row.processing_consent, row.free_project_confirmed = enabled, consent, free
    row.key_fingerprint = fingerprint(key) if key is not None else None
    session.commit()
    return settings(session, learner_id)


def allowed_key(session: Session, box: KeyBox, learner_id: int) -> str:
    row = session.get(InterviewSettings, learner_id)
    key = session.get(GradingKey, learner_id)
    if (
        row is None
        or not row.enabled
        or not row.processing_consent
        or not row.free_project_confirmed
        or key is None
        or key.provider != "gemini"
        or key.base_url != GEMINI_BASE_URL
        or row.key_fingerprint != fingerprint(key)
    ):
        raise Refused(
            409,
            "AI feedback is disabled. Self-review is available; check your own key and consent.",
        )
    decrypted = box.decrypt(key.key_ciphertext)
    if decrypted is None:
        raise Refused(409, "Your own Gemini key is unavailable. Use self-review.")
    return decrypted


def operation_out(row: InterviewOperation) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "prompt_id": row.prompt_id,
        "state": row.state,
        "feedback": row.result,
    }


def request_feedback(
    session: Session,
    box: KeyBox,
    learner: Learner,
    interview_id: uuid.UUID,
    operation_id: uuid.UUID,
    prompt_id: str,
    confirmed: bool,
    now: datetime,
) -> dict[str, Any]:
    with provider_lease(session, learner.id):
        return _request_feedback(
            session, box, learner, interview_id, operation_id, prompt_id, confirmed, now
        )


@contextmanager
def provider_lease(session: Session, learner_id: int) -> Iterator[None]:
    """An owner-level lock independent of deletable private evidence.

    A dedicated connection keeps the lock across reservation commits and network I/O.
    PostgreSQL releases it if the process dies; no timeout can release a live request.
    """
    with session.get_bind().engine.connect() as connection:
        acquired = connection.scalar(
            text("SELECT pg_try_advisory_lock(731924, :owner)"), {"owner": learner_id}
        )
        connection.commit()
        if not acquired:
            raise Refused(409, "A Gemini request is already in progress. Wait before retrying.")
        try:
            yield
        finally:
            connection.execute(
                text("SELECT pg_advisory_unlock(731924, :owner)"), {"owner": learner_id}
            )
            connection.commit()


def _request_feedback(
    session: Session,
    box: KeyBox,
    learner: Learner,
    interview_id: uuid.UUID,
    operation_id: uuid.UUID,
    prompt_id: str,
    confirmed: bool,
    now: datetime,
) -> dict[str, Any]:
    # Serialize reservations on the owner, including across separate sessions/tabs.
    session.execute(select(Learner.id).where(Learner.id == learner.id).with_for_update())
    interview = interviews.owned(session, learner.id, interview_id, now, lock=True)
    if interview is None:
        raise Refused(404, "Interview unavailable.")
    # Acquiring the owner lease proves no previous application request is still live.
    # Keep abandoned attempts charged and require a new manual idempotency ID to retry.
    session.execute(
        update(InterviewOperation)
        .where(InterviewOperation.learner_id == learner.id, InterviewOperation.state == "running")
        .values(state="interrupted")
    )
    existing = session.get(InterviewOperation, operation_id)
    if existing is not None:
        if (
            existing.learner_id != learner.id
            or existing.interview_id != interview_id
            or existing.prompt_id != prompt_id
            or existing.kind != "feedback"
        ):
            raise Refused(409, "Operation ID already used.")
        session.commit()
        return operation_out(existing)
    if not confirmed:
        raise Refused(422, "Confirm the response text before requesting feedback.")
    text = interview.responses.get(prompt_id)
    prompt = next(
        (InterviewPrompt.model_validate(p) for p in interview.prompts if p["id"] == prompt_id), None
    )
    if prompt is None or not text:
        raise Refused(
            422, "Save a response to this scenario first; skipped responses use self-review."
        )
    record = onboarding.active_stack(session, learner, interview.stack_id)
    if record is None or prompt.concept not in {
        p.concept for p in interviews.eligible(session, record, now)
    }:
        raise Refused(
            409, "This topic is no longer eligible for AI practice. Self-review is available."
        )
    key = allowed_key(session, box, learner.id)
    if session.scalar(
        select(InterviewOperation.id).where(
            InterviewOperation.learner_id == learner.id, InterviewOperation.state == "running"
        )
    ):
        raise Refused(409, "A Gemini request is already in progress. Wait before retrying.")
    count = (
        session.scalar(
            select(func.count())
            .select_from(InterviewOperation)
            .where(InterviewOperation.interview_id == interview.id)
        )
        or 0
    )
    if count >= 18:
        raise Refused(409, "The 18-request session budget is exhausted. Use self-review.")
    previous = session.scalar(
        select(InterviewOperation).where(
            InterviewOperation.interview_id == interview.id,
            InterviewOperation.prompt_id == prompt_id,
            InterviewOperation.kind == "feedback",
            InterviewOperation.state == "complete",
        )
    )
    if previous is not None:
        session.commit()
        return operation_out(previous)
    operation = InterviewOperation(
        id=operation_id,
        interview_id=interview.id,
        learner_id=learner.id,
        prompt_id=prompt_id,
        kind="feedback",
        state="running",
        created_at=now,
        response_text=text,
        result=None,
    )
    session.add(operation)
    session.commit()  # count failures and release reservation locks before network I/O
    state, result = "complete", None
    try:
        result = interview_provider.feedback(key, prompt, text)
    except interview_provider.ProviderUnavailable as error:
        state = error.state
    # A concurrent deletion must never resurrect private evidence.
    session.expire_all()
    saved = session.get(InterviewOperation, operation_id)
    if saved is None:
        raise Refused(404, "Interview deleted while processing.")
    try:
        allowed_key(session, box, learner.id)
    except Refused:
        state, result = "processing_disabled", None
    saved.state, saved.result = state, result
    session.commit()
    return operation_out(saved)
