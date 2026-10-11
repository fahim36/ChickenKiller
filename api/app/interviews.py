"""Owner-only self-review practice with immutable reviewed prompt snapshots."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import challenges, progress, weak_concepts
from app.content.interviews import InterviewPrompt
from app.models import (
    Concept,
    InterviewContent,
    InterviewRecording,
    InterviewSession,
    LearnerStack,
    Question,
)


def expire(session: Session, now: datetime) -> None:
    session.execute(delete(InterviewRecording).where(InterviewRecording.expires_at <= now))
    session.execute(delete(InterviewSession).where(InterviewSession.expires_at <= now))


def eligible(session: Session, record: LearnerStack, now: datetime) -> list[InterviewPrompt]:
    completed = progress.completed_lesson_ids(session, record.learner_id, record.stack_id)
    played = challenges.played_question_ids(session, record.learner_id, record.stack_id)
    studied = set(
        session.scalars(
            select(Concept.id)
            .join(Question, Question.concept_pk == Concept.pk)
            .where(
                Question.stack_id == record.stack_id,
                (Question.lesson_id.in_(completed)) | (Question.id.in_(played)),
            )
        )
    )
    weak = {
        c.id for c in weak_concepts.for_stack(session, record, now) if c.evidence.status == "weak"
    }
    prompts = [
        InterviewPrompt.model_validate(row.document)
        for row in session.scalars(
            select(InterviewContent).where(InterviewContent.stack_id == record.stack_id)
        )
    ]
    return sorted(
        (p for p in prompts if p.concept in studied),
        key=lambda p: (p.concept not in weak, p.id),
    )


def start(
    session: Session, record: LearnerStack, now: datetime, concepts: list[str]
) -> InterviewSession:
    available = eligible(session, record, now)
    if concepts and (
        len(concepts) > 3
        or len(set(concepts)) != len(concepts)
        or not set(concepts) <= {p.concept for p in available}
    ):
        raise ValueError("Choose up to three distinct studied topics.")
    selected: dict[str, InterviewPrompt] = {}
    for prompt in available:
        if not concepts or prompt.concept in concepts:
            selected.setdefault(prompt.concept, prompt)
    picked = [selected[c] for c in concepts] if concepts else list(selected.values())[:3]
    if not picked:
        raise ValueError(
            "Complete a Lesson or play a Daily Challenge to study a reviewed topic first."
        )
    row = InterviewSession(
        learner_id=record.learner_id,
        stack_id=record.stack_id,
        created_at=now,
        expires_at=now + timedelta(days=30),
        prompts=[p.model_dump(mode="json") for p in picked],
        responses={},
    )
    session.add(row)
    session.flush()
    return row


def practice_state(session: Session, row: InterviewSession, now: datetime) -> str:
    """Private history survives changes; new work must still use eligible reviewed content."""
    record = session.get(LearnerStack, (row.learner_id, row.stack_id))
    if record is None or not record.active:
        return "inactive_stack"
    for document in row.prompts:
        current = session.get(InterviewContent, (row.stack_id, document["id"]))
        if current is None or current.document["version"] != document["version"]:
            return "content_changed"
    studied = {prompt.concept for prompt in eligible(session, record, now)}
    if any(document["concept"] not in studied for document in row.prompts):
        return "topic_no_longer_studied"
    return "available"


def require_current(session: Session, row: InterviewSession, now: datetime) -> None:
    state = practice_state(session, row, now)
    if state != "available":
        raise ValueError(
            f"New practice is unavailable ({state}); original history and self-review remain."
        )


def owned(
    session: Session, learner_id: int, interview_id: uuid.UUID, now: datetime, *, lock: bool = False
) -> InterviewSession | None:
    query = select(InterviewSession).where(
        InterviewSession.id == interview_id,
        InterviewSession.learner_id == learner_id,
        InterviewSession.expires_at > now,
    )
    return session.scalar(query.with_for_update() if lock else query)
