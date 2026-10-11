"""Descriptive delayed performance on first recorded variants, not a causal estimate."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import (
    Answer,
    Concept,
    LearnerStack,
    Question,
    Retake,
    TargetedPractice,
    TargetedReviewVisit,
)


def record_visit(session: Session, record: LearnerStack, concept_id: str, now: datetime) -> None:
    session.execute(
        insert(TargetedReviewVisit)
        .values(
            learner_id=record.learner_id,
            stack_id=record.stack_id,
            concept_id=concept_id,
            day=now.astimezone(UTC).date(),
        )
        .on_conflict_do_nothing()
    )
    session.commit()


@dataclass(frozen=True)
class Summary:
    qualifying_answers: int
    correct_answers: int
    accuracy: float | None
    learners: int
    concepts: int
    uptake_days: int
    uptake_learners: int
    completed_practice_answers: int
    practice_learners: int
    retakes_total: int
    retakes_completed: int
    retakes_waived: int


def summary(session: Session, now: datetime) -> Summary:
    practices: dict[tuple[int, str, str], list[datetime]] = defaultdict(list)
    practiced_learners: set[int] = set()
    for answer, concept_id in session.execute(
        select(Answer, TargetedPractice.concept_id)
        .join(TargetedPractice, TargetedPractice.answer_id == Answer.id)
        .where(Answer.answered_at <= now)
    ):
        practices[(answer.learner_id, answer.stack_id, concept_id)].append(answer.answered_at)
        practiced_learners.add(answer.learner_id)
    seen: set[tuple[int, str, str]] = set()
    qualifying: list[tuple[Answer, str]] = []
    for answer, concept_id in session.execute(
        select(Answer, Concept.id)
        .join(
            Question, and_(Question.stack_id == Answer.stack_id, Question.id == Answer.question_id)
        )
        .join(Concept, Concept.pk == Question.concept_pk)
        .where(Answer.answered_at <= now, Question.retired_reason.is_(None))
        .order_by(Answer.answered_at, Answer.id)
    ):
        key = (answer.learner_id, answer.stack_id, answer.question_id)
        if key in seen:
            continue
        seen.add(key)
        # Any earlier stored answer means this is not a fresh recorded variant, including
        # unanswered/ungraded attempts. Retake performance is supporting evidence only.
        if (
            not answer.response
            or not answer.response.strip()
            or answer.correct is None
            or answer.context == "retake"
        ):
            continue
        preceding = [
            at
            for at in practices[(answer.learner_id, answer.stack_id, concept_id)]
            if at < answer.answered_at
        ]
        if not preceding:
            continue
        delay = (
            answer.answered_at.astimezone(UTC).date() - max(preceding).astimezone(UTC).date()
        ).days
        if 7 <= delay <= 14:
            qualifying.append((answer, concept_id))
    visits = session.scalars(
        select(TargetedReviewVisit).where(TargetedReviewVisit.day <= now.astimezone(UTC).date())
    ).all()
    retakes = session.scalars(select(Retake).where(Retake.created_at <= now)).all()
    correct = sum(a.correct is True for a, _ in qualifying)
    return Summary(
        len(qualifying),
        correct,
        correct / len(qualifying) if qualifying else None,
        len({a.learner_id for a, _ in qualifying}),
        len({(a.stack_id, c) for a, c in qualifying}),
        len(visits),
        len({v.learner_id for v in visits}),
        sum(len(times) for times in practices.values()),
        len(practiced_learners),
        len(retakes),
        sum(
            r.done_at is not None and r.done_at <= now and r.waived_reason is None for r in retakes
        ),
        sum(
            r.done_at is not None and r.done_at <= now and r.waived_reason is not None
            for r in retakes
        ),
    )
