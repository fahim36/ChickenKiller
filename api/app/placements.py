"""Owner-only placement lifecycle; every practice delivery shares its reservation lock."""

import random
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app import progress, question_exposure
from app.content.placement import PlacementPlan
from app.models import (
    DailyChallenge,
    LearnerStack,
    LessonQuizAttempt,
    PlacementAttempt,
    PlacementCoverage,
    PlacementReservation,
    Question,
    Retake,
    Stack,
    Syllabus,
    Week,
)
from app.placement_coverage import gaps
from app.placement_selection import FreshCoverageUnavailable, draw_lesson


def lock(session: Session, learner_id: int, stack_id: str) -> None:
    session.execute(
        text("SELECT pg_advisory_xact_lock_shared(hashtextextended(:key, 0))"),
        {"key": f"content:{stack_id}"},
    )
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"practice:{learner_id}:{stack_id}"},
    )


def release(session: Session, row: PlacementAttempt, state: str, reason: str | None = None) -> None:
    row.state, row.reason = state, reason
    session.execute(delete(PlacementReservation).where(PlacementReservation.attempt_id == row.id))
    session.flush()


def current_plan(session: Session, stack_id: str, week_id: str) -> PlacementCoverage | None:
    stack = session.get(Stack, stack_id, populate_existing=True)
    return (
        None
        if stack is None or stack.current_syllabus_pk is None
        else session.get(PlacementCoverage, (stack.current_syllabus_pk, week_id))
    )


def reconcile(session: Session, row: PlacementAttempt) -> None:
    if row.state != "open":
        return
    plan = current_plan(session, row.stack_id, row.week_id)
    ids = [q["id"] for q in row.questions]
    active = set(
        session.scalars(
            select(Question.id).where(
                Question.stack_id == row.stack_id,
                Question.id.in_(ids),
                Question.retired_reason.is_(None),
            )
        )
    )
    if plan is None or plan.teaching_revision != row.teaching_revision:
        release(
            session,
            row,
            "cancelled",
            "The Week's teaching or reviewed coverage changed. "
            "Start a fresh attempt if coverage is available.",
        )
    elif active != set(ids):
        release(
            session,
            row,
            "cancelled",
            "A Question in this attempt was retired. "
            "Start a fresh attempt if coverage is available.",
        )


def open_attempt(session: Session, learner_id: int, stack_id: str) -> PlacementAttempt | None:
    row = session.scalar(
        select(PlacementAttempt)
        .where(
            PlacementAttempt.learner_id == learner_id,
            PlacementAttempt.stack_id == stack_id,
            PlacementAttempt.state == "open",
        )
        .execution_options(populate_existing=True)
    )
    if row is not None:
        reconcile(session, row)
    return row if row is not None and row.state == "open" else None


def reserved(session: Session, learner_id: int, stack_id: str) -> set[str]:
    return set(
        session.scalars(
            select(PlacementReservation.question_id).where(
                PlacementReservation.learner_id == learner_id,
                PlacementReservation.stack_id == stack_id,
            )
        )
    )


def guard_lesson(session: Session, record: LearnerStack, lesson_id: str) -> None:
    lock(session, record.learner_id, record.stack_id)
    row = open_attempt(session, record.learner_id, record.stack_id)
    if row is not None and lesson_id in {q["lesson"] for q in row.questions}:
        raise HTTPException(
            409,
            "Resume or abandon your Placement Quiz before a Lesson Quiz or Retake in this Week.",
        )


def unavailable_questions(session: Session, record: LearnerStack) -> set[str]:
    ids = question_exposure.seen(session, record.learner_id, record.stack_id)
    # Frozen and upcoming Challenges keep their original Questions available during placement.
    for values in session.scalars(
        select(DailyChallenge.question_ids).where(DailyChallenge.stack_id == record.stack_id)
    ):
        ids.update(values)
    for values in session.scalars(
        select(LessonQuizAttempt.question_ids).where(
            LessonQuizAttempt.learner_id == record.learner_id,
            LessonQuizAttempt.stack_id == record.stack_id,
            LessonQuizAttempt.submitted_at.is_(None),
        )
    ):
        ids.update(values)
    for values in session.scalars(
        select(Retake.asked_question_ids).where(
            Retake.learner_id == record.learner_id,
            Retake.stack_id == record.stack_id,
            Retake.done_at.is_(None),
        )
    ):
        ids.update(values)
    return ids | reserved(session, record.learner_id, record.stack_id)


def draw(
    session: Session, record: LearnerStack, row: PlacementCoverage, rng: random.Random
) -> list[Question]:
    plan = PlacementPlan.model_validate(row.document)
    if gaps(session, plan):
        raise FreshCoverageUnavailable(plan.week)
    blocked = unavailable_questions(session, record)
    result: list[Question] = []
    for lesson in plan.lessons:
        candidates = list(
            session.scalars(
                select(Question).where(
                    Question.stack_id == record.stack_id,
                    Question.id.in_(lesson.questions),
                    Question.lesson_id == lesson.lesson,
                    Question.retired_reason.is_(None),
                    Question.type.in_(["multiple_choice", "multiple_select"]),
                )
            )
        )
        by_id = {q.id: q for q in candidates}
        picked = draw_lesson(lesson, {q.id: q.concept.id for q in candidates}, blocked, rng)
        result.extend(by_id[qid] for qid in picked)
    return result


def eligibility(session: Session, record: LearnerStack, week_id: str) -> dict[str, Any]:
    lock(session, record.learner_id, record.stack_id)
    session.refresh(record.stack)
    existing = open_attempt(session, record.learner_id, record.stack_id)
    if existing:
        return {
            "available": False,
            "reason": "Resume your unfinished Placement Quiz.",
            "attempt_id": str(existing.id),
            "week_id": existing.week_id,
        }
    completed = progress.completed_lesson_ids(session, record.learner_id, record.stack_id)
    weeks = list(
        session.scalars(
            select(Week)
            .where(Week.syllabus_pk == record.stack.current_syllabus_pk)
            .order_by(Week.position)
        )
    )
    next_week = next(
        (w for w in weeks if any(lesson.id not in completed for lesson in w.lessons)), None
    )
    reason: str | None = None
    if next_week is None or next_week.id != week_id:
        reason = "Placement is offered only for your earliest incomplete Week."
    elif (
        session.scalar(
            select(Retake.id)
            .join(LessonQuizAttempt)
            .where(
                Retake.learner_id == record.learner_id,
                Retake.stack_id == record.stack_id,
                Retake.done_at.is_(None),
                LessonQuizAttempt.lesson_id.in_([lesson.id for lesson in next_week.lessons]),
            )
        )
        is not None
    ):
        reason = "Clear this Week's pending Retakes before placement."
    plan = current_plan(session, record.stack_id, week_id)
    if reason is None and plan is None:
        reason = "No reviewed placement coverage is available for this Week."
    if reason is None and plan is not None:
        submitted = session.scalar(
            select(PlacementAttempt.id).where(
                PlacementAttempt.learner_id == record.learner_id,
                PlacementAttempt.stack_id == record.stack_id,
                PlacementAttempt.week_id == week_id,
                PlacementAttempt.teaching_revision == plan.teaching_revision,
                PlacementAttempt.state == "submitted",
            )
        )
        if submitted is not None:
            reason = (
                "You already submitted placement for this teaching revision. "
                "Continue the Lesson path."
            )
        else:
            try:
                draw(session, record, plan, random.Random(0))
            except FreshCoverageUnavailable:
                reason = (
                    "Not enough unseen Questions cover every essential Concept. "
                    "Continue the Lesson path."
                )
    return {"available": reason is None, "reason": reason, "attempt_id": None, "week_id": week_id}


def snapshot(q: Question) -> dict[str, Any]:
    return {
        "id": q.id,
        "lesson": q.lesson_id,
        "concept": q.concept.id,
        "type": q.type,
        "prompt": q.prompt,
        "choices": q.choices or [],
        "answer": q.answer,
        "answers": q.answers,
        "explanation": q.explanation,
        "sources": [
            {
                "url": s.url,
                "title": s.title,
                "publisher": s.publisher,
                "accessed": str(s.accessed),
                "claim": s.claim,
            }
            for s in q.sources
        ],
    }


def start(
    session: Session, record: LearnerStack, week_id: str, now: datetime, rng: random.Random
) -> PlacementAttempt:
    info = eligibility(session, record, week_id)
    if info["attempt_id"]:
        return session.get_one(PlacementAttempt, uuid.UUID(info["attempt_id"]))
    if not info["available"]:
        session.commit()  # persist any stale-attempt cancellation
        raise HTTPException(409, info["reason"])
    plan = current_plan(session, record.stack_id, week_id)
    assert plan is not None
    questions = draw(session, record, plan, rng)
    syllabus = session.get_one(Syllabus, plan.syllabus_pk)
    row = PlacementAttempt(
        id=uuid.uuid4(),
        learner_id=record.learner_id,
        stack_id=record.stack_id,
        week_id=week_id,
        syllabus_version=syllabus.version,
        teaching_revision=plan.teaching_revision,
        state="open",
        started_at=now,
        questions=[snapshot(q) for q in questions],
        responses={},
    )
    session.add(row)
    session.flush()
    session.add_all(
        [
            PlacementReservation(
                learner_id=record.learner_id,
                stack_id=record.stack_id,
                question_id=q.id,
                attempt_id=row.id,
            )
            for q in questions
        ]
    )
    session.commit()
    return row


def owned(session: Session, learner_id: int, attempt_id: uuid.UUID) -> PlacementAttempt:
    row = session.scalar(
        select(PlacementAttempt).where(
            PlacementAttempt.id == attempt_id, PlacementAttempt.learner_id == learner_id
        )
    )
    if row is None:
        raise HTTPException(404, "Placement Quiz not found")
    lock(session, learner_id, row.stack_id)
    session.refresh(row)
    reconcile(session, row)
    return row


def output(session: Session, row: PlacementAttempt, now: datetime) -> dict[str, Any]:
    if row.state == "open":
        questions = list(
            session.scalars(
                select(Question).where(
                    Question.stack_id == row.stack_id,
                    Question.id.in_([q["id"] for q in row.questions]),
                )
            )
        )
        question_exposure.deliver(session, row.learner_id, questions, now, placement_id=row.id)
    public = [
        {
            key: value
            for key, value in q.items()
            if row.state == "submitted"
            or key not in {"answer", "answers", "explanation", "sources"}
        }
        for q in row.questions
    ]
    session.commit()
    return {
        "id": str(row.id),
        "stack_id": row.stack_id,
        "week_id": row.week_id,
        "state": row.state,
        "reason": row.reason,
        "questions": public,
        "responses": row.responses,
        "result": row.result,
    }
