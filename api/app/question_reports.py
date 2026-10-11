"""After-answer content feedback, isolated from scoring and learning progress."""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Answer, Learner, Question, QuestionReport


def question(session: Session, stack_id: str, question_id: str, *, lock: bool = False) -> Question:
    query = select(Question).where(Question.stack_id == stack_id, Question.id == question_id)
    result = session.scalar(query.with_for_update() if lock else query)
    if result is None:
        raise HTTPException(404, "Question not found")
    return result


def answered(session: Session, learner_id: int, stack_id: str, question_id: str) -> bool:
    return (
        session.scalar(
            select(Answer.id)
            .where(
                Answer.learner_id == learner_id,
                Answer.stack_id == stack_id,
                Answer.question_id == question_id,
                Answer.response.is_not(None),
                func.length(func.trim(Answer.response)) > 0,
            )
            .limit(1)
        )
        is not None
    )


def unresolved(
    session: Session, learner_id: int, stack_id: str, question_id: str
) -> QuestionReport | None:
    return session.scalar(
        select(QuestionReport).where(
            QuestionReport.learner_id == learner_id,
            QuestionReport.stack_id == stack_id,
            QuestionReport.question_id == question_id,
            QuestionReport.status.in_(("open", "accepted")),
        )
    )


def save(
    session: Session,
    learner_id: int,
    stack_id: str,
    question_id: str,
    category: str,
    note: str | None,
    now: datetime,
) -> QuestionReport:
    # Serialize creation and edits even before a report row exists. The partial unique index
    # independently protects unresolved uniqueness for every writer.
    session.scalar(select(Learner).where(Learner.id == learner_id).with_for_update())
    current = question(session, stack_id, question_id, lock=True)
    if current.retired:
        raise HTTPException(409, {"code": "question_retired", "message": current.retired_reason})
    if not answered(session, learner_id, stack_id, question_id):
        raise HTTPException(409, "Answer this Question before reporting it.")
    report = unresolved(session, learner_id, stack_id, question_id)
    if report is not None and report.status != "open":
        raise HTTPException(409, "Only Open reports can be edited.")
    if report is None:
        report = QuestionReport(
            learner_id=learner_id,
            stack_id=stack_id,
            question_id=question_id,
            created_at=now,
            status="open",
        )
        session.add(report)
    report.category, report.note, report.updated_at = category, note, now
    session.commit()
    return report
