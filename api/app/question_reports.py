"""After-answer content feedback, isolated from scoring and learning progress."""

from datetime import datetime
from uuid import UUID

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
    session: Session, learner_id: int, stack_id: str, question_id: str, *, lock: bool = False
) -> QuestionReport | None:
    query = select(QuestionReport).where(
        QuestionReport.learner_id == learner_id,
        QuestionReport.stack_id == stack_id,
        QuestionReport.question_id == question_id,
        QuestionReport.status.in_(("open", "accepted")),
    )
    return session.scalar(query.with_for_update() if lock else query)


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
    report = unresolved(session, learner_id, stack_id, question_id, lock=True)
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


def decide(
    session: Session, report_id: UUID, status: str, explanation: str, now: datetime
) -> QuestionReport:
    report = session.scalar(
        select(QuestionReport).where(QuestionReport.id == report_id).with_for_update()
    )
    if report is None:
        raise HTTPException(404, "Report not found")
    if report.status != "open":
        raise HTTPException(409, "This report has already been decided.")
    report.status = status
    report.explanation = explanation
    report.updated_at = now
    session.commit()
    return report


def associate_correction(
    session: Session, report_id: UUID, kind: str, replacement_id: str | None, now: datetime
) -> QuestionReport:
    report = session.scalar(
        select(QuestionReport).where(QuestionReport.id == report_id).with_for_update()
    )
    if report is None:
        raise HTTPException(404, "Report not found")
    if report.status != "accepted":
        raise HTTPException(409, "Associate a correction with an accepted report.")
    if (kind == "replacement") != (
        replacement_id is not None
    ) or replacement_id == report.question_id:
        raise HTTPException(
            422,
            "A replacement needs a different Question ID; a retirement has no replacement.",
        )
    if report.correction_kind == kind and report.replacement_id == replacement_id:
        session.commit()
        return report
    report.correction_kind = kind
    report.replacement_id = replacement_id
    report.updated_at = now
    session.commit()
    return report


def resolve_imported(
    session: Session,
    stack_id: str,
    retirements: dict[str, str | None],
    active_question_ids: set[str],
    now: datetime,
) -> None:
    """Flush resolutions in the import transaction; the importing caller must commit.

    The original must be retired with exactly the expected replacement (or none). A
    replacement must actually exist and be active in this Stack. Drafts have no effect.
    """
    reports = session.scalars(
        select(QuestionReport)
        .where(
            QuestionReport.stack_id == stack_id,
            QuestionReport.status == "accepted",
            QuestionReport.correction_kind.is_not(None),
        )
        .order_by(QuestionReport.id)
        .with_for_update()
    ).all()
    for report in reports:
        if (
            report.question_id not in retirements
            or retirements[report.question_id] != report.replacement_id
        ):
            continue
        original = question(session, stack_id, report.question_id)
        if not original.retired or original.replaced_by != report.replacement_id:
            continue
        if report.correction_kind == "replacement":
            if report.replacement_id not in active_question_ids:
                continue
            replacement = session.scalar(
                select(Question).where(
                    Question.stack_id == stack_id,
                    Question.id == report.replacement_id,
                )
            )
            if replacement is None or replacement.retired:
                continue
        report.status = "resolved"
        report.resolved_at = now
        report.updated_at = now
        report.resolution_reason = original.retired_reason
    session.flush()
