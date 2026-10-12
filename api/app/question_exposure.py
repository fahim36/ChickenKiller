"""Learner-only prompt delivery evidence; selection and Admin reads are not exposure."""

import uuid
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Answer, PlacementReservation, Question, QuestionExposure


def deliver(
    session: Session,
    learner_id: int,
    questions: Iterable[Question],
    now: datetime,
    *,
    placement_id: uuid.UUID | None = None,
) -> None:
    from fastapi import HTTPException

    from app import placements

    questions = list(questions)
    for stack_id in sorted({q.stack_id for q in questions}):
        placements.lock(session, learner_id, stack_id)
        placements.open_attempt(session, learner_id, stack_id)
    for q in questions:
        reservation = session.get(PlacementReservation, (learner_id, q.stack_id, q.id))
        if reservation is not None and reservation.attempt_id != placement_id:
            raise HTTPException(
                409, "This Question is reserved for your unfinished Placement Quiz."
            )
    rows = {
        (q.stack_id, q.id): {
            "learner_id": learner_id,
            "stack_id": q.stack_id,
            "question_id": q.id,
            "first_seen_at": now,
        }
        for q in questions
    }
    if rows:
        session.execute(
            insert(QuestionExposure).values(list(rows.values())).on_conflict_do_nothing()
        )
        session.commit()


def seen(session: Session, learner_id: int, stack_id: str) -> set[str]:
    exposed = set(
        session.scalars(
            select(QuestionExposure.question_id).where(
                QuestionExposure.learner_id == learner_id, QuestionExposure.stack_id == stack_id
            )
        )
    )
    return exposed | set(
        session.scalars(
            select(Answer.question_id).where(
                Answer.learner_id == learner_id, Answer.stack_id == stack_id
            )
        )
    )
