"""Owner-only self-review practice with immutable reviewed prompt snapshots."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import challenges, progress, weak_concepts
from app.content.interviews import InterviewPrompt
from app.models import Concept, InterviewContent, InterviewSession, LearnerStack, Question


def expire(session: Session, now: datetime) -> None:
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


def owned(
    session: Session, learner_id: int, interview_id: uuid.UUID, now: datetime, *, lock: bool = False
) -> InterviewSession | None:
    query = select(InterviewSession).where(
        InterviewSession.id == interview_id,
        InterviewSession.learner_id == learner_id,
        InterviewSession.expires_at > now,
    )
    return session.scalar(query.with_for_update() if lock else query)
