"""One optional next action, composed from existing practice and eligibility rules."""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import lessons, progress, retakes, reviews, weak_concepts
from app.models import Answer, LearnerStack, LessonQuizAttempt, Retake


@dataclass(frozen=True)
class Action:
    kind: Literal["retake", "concept_review", "lesson", "review", "complete"]
    title: str
    reason: str
    stack_id: str | None = None
    lesson_id: str | None = None
    attempt_id: str | None = None
    concept_id: str | None = None


@dataclass(frozen=True)
class WeakConcept:
    stack_id: str
    stack_name: str
    concept: weak_concepts.ConceptEvidence


@dataclass(frozen=True)
class Guidance:
    action: Action
    weak_concepts: list[WeakConcept]


@dataclass(frozen=True, order=True)
class PendingRetake:
    created_at: datetime
    stack_id: str
    lesson_id: str
    retake_id: str
    attempt_id: str


def for_learner(
    session: Session, records: Sequence[LearnerStack], now: datetime, rng: random.Random
) -> Guidance:
    """Resolve content retirement before ranking pending Retakes; never change scores."""
    by_stack = {r.stack_id: r for r in records}
    pending: list[PendingRetake] = []
    attempts = session.scalars(
        select(LessonQuizAttempt)
        .join(Retake, Retake.lesson_quiz_attempt_id == LessonQuizAttempt.id)
        .where(
            LessonQuizAttempt.learner_id == records[0].learner_id,
            LessonQuizAttempt.stack_id.in_(by_stack),
            LessonQuizAttempt.passed.is_(True),
            Retake.done_at.is_(None),
        )
        .order_by(LessonQuizAttempt.submitted_at, LessonQuizAttempt.stack_id, LessonQuizAttempt.id)
        .distinct()
    ).all()
    for attempt in attempts:
        state = retakes.open_retakes(
            session, by_stack[attempt.stack_id], attempt.lesson_id, attempt.id, rng, now
        )
        pending.extend(
            PendingRetake(
                p.retake.created_at,
                attempt.stack_id,
                attempt.lesson_id,
                str(p.retake.id),
                str(attempt.id),
            )
            for p in state.pending
        )

    weak = sorted(
        [
            WeakConcept(r.stack_id, r.stack.name, c)
            for r in records
            for c in weak_concepts.for_stack(session, r, now)
            if c.evidence.status == "weak"
        ],
        key=lambda w: (*weak_concepts.rank(w.concept), w.stack_id),
    )
    due = reviews.review_set(session, records, now, limit=None)
    due_concepts = {(q.stack.id, q.question.concept.id) for q in due}
    if pending:
        oldest = min(pending)
        action = Action(
            "retake",
            "Finish your oldest pending Retake",
            "This passed Lesson Quiz is waiting for its remaining Retakes.",
            oldest.stack_id,
            oldest.lesson_id,
            oldest.attempt_id,
        )
    elif target := next((w for w in weak if (w.stack_id, w.concept.id) in due_concepts), None):
        action = Action(
            "concept_review",
            f"Practise {target.concept.name}",
            f"You missed {target.concept.evidence.recent_missed_questions} distinct active "
            "Questions in 30 UTC Days. Due Review is available.",
            target.stack_id,
            concept_id=target.concept.id,
        )
    else:
        latest = dict(
            session.execute(
                select(Answer.stack_id, func.max(Answer.answered_at))
                .where(
                    Answer.learner_id == records[0].learner_id,
                    Answer.stack_id.in_(by_stack),
                    Answer.answered_at <= now,
                    Answer.response.is_not(None),
                    func.length(func.trim(Answer.response)) > 0,
                    Answer.context.in_(("lesson_quiz", "daily_challenge", "retake", "review")),
                )
                .group_by(Answer.stack_id)
            ).all()
        )
        ordered = sorted(
            records,
            key=lambda r: (
                r.stack_id not in latest,
                -latest[r.stack_id].timestamp() if r.stack_id in latest else 0,
                r.stack_id,
            ),
        )
        action = Action(
            "complete",
            "You're caught up",
            "No Lesson or due practice remains. "
            "Explore your Materials and Milestones whenever you like.",
        )
        for record in ordered:
            states = progress.lesson_states(session, record.learner_id, record.stack_id)
            unlocked = next((lid for lid, state in states.items() if state == "unlocked"), None)
            if unlocked is not None:
                lesson = lessons.find_current_lesson(session, record.stack_id, unlocked)
                assert lesson is not None
                action = Action(
                    "lesson",
                    f"Continue: {lesson.title}",
                    "Among Stacks with an available Lesson, this one has your most recent "
                    "recorded practice."
                    if record.stack_id in latest
                    else "No recorded practice yet; start with this Stack's next Unlocked Lesson.",
                    record.stack_id,
                    unlocked,
                )
                break
        else:
            if due:
                action = Action(
                    "review",
                    "Review due Questions",
                    "Your Lesson path is complete; optional Review has Questions due.",
                )
    return Guidance(action, weak[:3])
