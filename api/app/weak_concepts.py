"""Concept guidance from recorded practice, never a mastery estimate or progress gate."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app import lessons
from app.models import Answer, Concept, LearnerStack, Question

Status = Literal["weak", "recovered", "expired", "insufficient"]


@dataclass(frozen=True)
class Outcome:
    """An actually answered, graded outcome on an active Question."""

    question_id: str
    answered_at: datetime
    correct: bool


@dataclass(frozen=True)
class Evidence:
    status: Status
    recent_missed_questions: int
    latest_miss: datetime | None
    recovery_days: int
    recovery_questions: int


def evidence(outcomes: Sequence[Outcome], now: datetime) -> Evidence:
    """Trigger on two distinct misses in the current and preceding 29 UTC Days."""
    start = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=29
    )
    all_misses = [o for o in outcomes if not o.correct and o.answered_at <= now]
    misses = [o for o in all_misses if o.answered_at >= start]
    count = len({o.question_id for o in misses})
    latest = max((o.answered_at for o in all_misses), default=None)
    correct = [
        o for o in outcomes if o.correct and latest is not None and latest < o.answered_at <= now
    ]
    days = len({o.answered_at.astimezone(UTC).date() for o in correct})
    questions = len({o.question_id for o in correct})
    status: Status = "insufficient"
    if count >= 2:
        status = "recovered" if days >= 3 and questions >= 2 else "weak"
    else:
        seen: dict[str, datetime] = {}
        for miss in sorted(all_misses, key=lambda o: o.answered_at):
            floor = miss.answered_at.astimezone(UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=29)
            seen = {qid: at for qid, at in seen.items() if at >= floor}
            seen[miss.question_id] = miss.answered_at
            if len(seen) >= 2:
                status = "expired"
                break
    return Evidence(status, count, latest, days, questions)


@dataclass(frozen=True)
class ConceptEvidence:
    id: str
    name: str
    active_questions: int
    lesson_id: str | None
    lesson_title: str | None
    evidence: Evidence


def for_stack(session: Session, record: LearnerStack, now: datetime) -> list[ConceptEvidence]:
    """Read only this Learner's answered/graded practice on currently active Questions.

    Retired Questions disappear from trigger and recovery evidence, without changing history.
    Removed or untagged teaching Lessons produce no link.
    """
    concepts = session.scalars(select(Concept).where(Concept.stack_id == record.stack_id)).all()
    bank = session.scalars(
        select(Question)
        .where(Question.stack_id == record.stack_id, Question.retired_reason.is_(None))
        .order_by(Question.position, Question.id)
    ).all()
    questions: dict[int, list[Question]] = {c.pk: [] for c in concepts}
    outcomes: dict[int, list[Outcome]] = {c.pk: [] for c in concepts}
    for question in bank:
        questions[question.concept_pk].append(question)
    rows = session.execute(
        select(Answer, Question.concept_pk)
        .join(
            Question, and_(Question.stack_id == Answer.stack_id, Question.id == Answer.question_id)
        )
        .where(
            Answer.learner_id == record.learner_id,
            Answer.stack_id == record.stack_id,
            Answer.context.in_(("lesson_quiz", "daily_challenge", "retake", "review")),
            Answer.correct.is_not(None),
            Question.retired_reason.is_(None),
        )
    ).all()
    for answer, concept_pk in rows:
        if answer.response is not None and answer.response.strip() and answer.correct is not None:
            outcomes[concept_pk].append(
                Outcome(answer.question_id, answer.answered_at, answer.correct)
            )
    syllabus = lessons.current_syllabus(session, record.stack_id)
    teaching = (
        {}
        if syllabus is None
        else {lesson.id: lesson for week in syllabus.weeks for lesson in week.lessons}
    )
    result = []
    for concept in concepts:
        linked = next(
            (teaching[q.lesson_id] for q in questions[concept.pk] if q.lesson_id in teaching), None
        )
        result.append(
            ConceptEvidence(
                concept.id,
                concept.name,
                len(questions[concept.pk]),
                None if linked is None else linked.id,
                None if linked is None else linked.title,
                evidence(outcomes[concept.pk], now),
            )
        )
    return sorted(result, key=rank)


def rank(concept: ConceptEvidence) -> tuple[bool, int, float, str]:
    """Weak first: distinct recent misses, newest miss, stable Concept ID."""
    current = concept.evidence
    return (
        current.status != "weak",
        -current.recent_missed_questions if current.status == "weak" else 0,
        -(current.latest_miss.timestamp())
        if current.status == "weak" and current.latest_miss
        else 0,
        concept.id,
    )
