"""Learner-only prompt delivery evidence; selection and Admin reads are not exposure."""

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Answer, Question, QuestionExposure


def deliver(
    session: Session, learner_id: int, questions: Iterable[Question], now: datetime
) -> None:
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
