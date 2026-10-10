"""Retakes (#8): after a Lesson Quiz that met the Pass Mark with Missed Questions, each Missed
Question is retaken on a sibling Question (same Concept, never the original), and the Lesson
becomes a Completed Lesson when every Retake is correct or waived for obsolete content.

- **Opening** (`open_retakes`) makes one `Retake` per Missed Question of a passed attempt and
  asks its first sibling. It is idempotent: the submit route calls it right after submitting,
  and reading the Retakes calls it again, so an interrupted request never strands a Lesson.
- **Answering** (`answer_retake`) marks the sibling asked with `marking.mark`, the same rules
  as the Lesson Quiz: a written sibling is graded against its Model Answer (#7). Correct: that
  Retake is done, and the last one done completes the Lesson. Wrong: its Explanation, Sources
  and Materials (and the grader's feedback) are shown and another sibling is asked
  (`quiz.pick_sibling`: unused ones first, then cycling, never the original). A Concept with
  no active sibling left is waived with a content-gap reason. A retired original also waives
  its requirement; a retired waiting sibling is replaced. No waiver creates an Answer.
  If grading fails, nothing is recorded and the Learner
  answers again.
- Siblings come from the Stack's Question Bank, and are never Retired Questions.
- Every answer is an `Answer` with `context='retake'`, so a wrong sibling is a Missed Question
  too (`quizzes.missed_questions`).

Retakes are keyed by the Learner and the attempt, not guarded by `UnlockedLesson`, so Retakes
already under way can always be finished.

A sibling may be of any type, whatever the Missed Question's type: a missed multiple-choice
Question can be retaken on a multiple-select sibling and vice versa.
"""

import random
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import progress, quiz
from app.grading import Grader
from app.marking import AnswerTooLong, GradingFailed, NotAChoice, mark
from app.models import Answer, LearnerStack, LessonQuizAttempt, Question, Retake

RETAKE = "retake"
"""`Answer.context` for an answer given in a Retake."""

RETAKE_TYPES = ("multiple_choice", "multiple_select", "written")
"""Question types a Retake may ask: every one, since `marking.mark` marks them all (written
Questions are legacy, ADR-0008, and only asked while one on the Concept isn't retired)."""


class RetakeNotFound(Exception):
    """No such Retake (or attempt) for this Learner, Stack and Lesson."""


class RetakeDone(Exception):
    """The Retake was already answered correctly."""


@dataclass(frozen=True)
class PendingRetake:
    retake: Retake
    question: Question
    """The sibling waiting for an answer. It includes the correct answer: never send it."""


@dataclass(frozen=True)
class RetakeState:
    attempt: LessonQuizAttempt
    pending: list[PendingRetake]
    """In the order the Missed Questions were asked in the quiz."""
    lesson_completed: bool
    notices: list["RetakeNotice"]


@dataclass(frozen=True)
class RetakeNotice:
    retake_id: uuid.UUID
    message: str
    waived: bool


@dataclass(frozen=True)
class RetakeResult:
    retake: Retake
    question: Question | None
    """The sibling just answered."""
    response: str | None
    correct: bool | None
    feedback: str | None
    """The grader's one line, for a graded written answer."""
    next_question: Question | None
    """Another sibling to try, after a wrong answer."""
    pending: int
    """Retakes of the attempt still waiting for a correct answer."""
    lesson_completed: bool
    notices: list[RetakeNotice]
    waived: bool = False


def open_retakes(
    session: Session,
    record: LearnerStack,
    lesson_id: str,
    attempt_id: uuid.UUID,
    rng: random.Random,
    now: datetime,
) -> RetakeState:
    """The pending Retakes of a submitted attempt, opening any not opened yet. A passed attempt
    with nothing pending completes the Lesson. An attempt below the Pass Mark has no Retakes.

    Raises RetakeNotFound for an attempt that isn't the Learner's or isn't submitted.
    """
    attempt = session.scalar(
        select(LessonQuizAttempt)
        .where(
            LessonQuizAttempt.id == attempt_id,
            LessonQuizAttempt.learner_id == record.learner_id,
            LessonQuizAttempt.stack_id == record.stack_id,
            LessonQuizAttempt.lesson_id == lesson_id,
            LessonQuizAttempt.submitted_at.is_not(None),
        )
        .with_for_update()
    )
    if attempt is None:
        raise RetakeNotFound(attempt_id)
    if not attempt.passed:
        session.commit()
        return RetakeState(attempt, [], lesson_completed=False, notices=[])

    missed = session.scalars(
        select(Answer.question_id).where(
            Answer.lesson_quiz_attempt_id == attempt.id, Answer.correct.is_(False)
        )
    ).all()
    opened = set(
        session.scalars(
            select(Retake.missed_question_id).where(Retake.lesson_quiz_attempt_id == attempt.id)
        )
    )
    for question_id in sorted(set(missed) - opened):
        original = _question(session, attempt, question_id)
        sibling = _next_question(session, original, [], rng)
        session.execute(
            insert(Retake)
            .values(
                id=uuid.uuid4(),
                learner_id=record.learner_id,
                stack_id=record.stack_id,
                lesson_quiz_attempt_id=attempt.id,
                missed_question_id=question_id,
                asked_question_ids=[] if sibling is None else [sibling],
                created_at=now,
            )
            .on_conflict_do_nothing()
        )

    _reconcile(session, attempt, rng, now)
    pending = _pending(session, attempt)
    notices = _notices(session, attempt)
    if pending:
        session.commit()
        return RetakeState(attempt, pending, lesson_completed=False, notices=notices)
    progress.complete_lesson(
        session, record, attempt.lesson_id, now, attempt.syllabus_version
    )  # commits
    return RetakeState(attempt, [], lesson_completed=True, notices=notices)


def answer_retake(
    session: Session,
    record: LearnerStack,
    lesson_id: str,
    retake_id: uuid.UUID,
    response: str | None,
    grader: Grader,
    rng: random.Random,
    now: datetime,
    question_id: str | None = None,
) -> RetakeResult:
    """Mark and record the answer to a Retake's waiting sibling: a choice ID or a written
    answer. None (or a blank written answer) is unanswered, so wrong.

    Raises RetakeNotFound, RetakeDone, NotAChoice, AnswerTooLong or GradingFailed; nothing is
    recorded then, and the same sibling waits for another answer. A written answer is graded
    while the Retake's row is locked, so a double submission can't grade twice.
    """
    retake = session.scalar(
        select(Retake)
        .join(LessonQuizAttempt, LessonQuizAttempt.id == Retake.lesson_quiz_attempt_id)
        .where(
            Retake.id == retake_id,
            Retake.learner_id == record.learner_id,
            Retake.stack_id == record.stack_id,
            LessonQuizAttempt.lesson_id == lesson_id,
        )
        .with_for_update(of=LessonQuizAttempt)
    )
    if retake is None:
        raise RetakeNotFound(retake_id)
    # A joined SELECT may have read the Retake before waiting on the attempt lock.
    session.refresh(retake)
    if retake.done_at is not None and retake.waived_reason is None:
        raise RetakeDone(retake_id)
    attempt = session.get_one(LessonQuizAttempt, retake.lesson_quiz_attempt_id)
    if not attempt.passed:
        raise RetakeNotFound(retake_id)
    waiting = retake.asked_question_ids[-1] if retake.asked_question_ids else None
    _reconcile(session, attempt, rng, now)
    current = retake.asked_question_ids[-1] if retake.asked_question_ids else None
    if (
        retake.done_at is not None
        or current != waiting
        or (question_id is not None and question_id != current)
        or (question_id is None and retake.replacement_notice is not None)
    ):
        pending = len(_pending(session, attempt))
        completed = pending == 0
        notices = _notices(session, attempt)
        refreshed = (
            None
            if retake.done_at is not None or current is None
            else _question(session, attempt, current)
        )
        if completed:
            progress.complete_lesson(session, record, lesson_id, now, attempt.syllabus_version)
        else:
            session.commit()
        return RetakeResult(
            retake,
            None,
            None,
            None,
            None,
            refreshed,
            pending,
            completed,
            notices,
            retake.waived_reason is not None,
        )
    question = _question(session, attempt, retake.asked_question_ids[-1])
    try:
        marked = mark(question, response, grader)
    except (NotAChoice, AnswerTooLong, GradingFailed):
        session.rollback()  # releases the lock; nothing was written
        raise
    correct = marked.correct
    session.add(
        Answer(
            learner_id=record.learner_id,
            stack_id=record.stack_id,
            question_id=question.id,
            context=RETAKE,
            retake_id=retake.id,
            response=response,
            correct=correct,
            feedback=marked.feedback,
            answered_at=now,
        )
    )

    next_question = None
    if correct:
        retake.done_at = now
    else:
        original = _question(session, attempt, retake.missed_question_id)
        next_id = _next_question(session, original, retake.asked_question_ids, rng)
        if next_id is None:
            retake.done_at = now
            retake.waived_reason = "Retake waived: no active sibling remains on this Concept."
        else:
            retake.asked_question_ids = [*retake.asked_question_ids, next_id]
            next_question = _question(session, attempt, next_id)
    session.flush()

    pending = len(_pending(session, attempt))
    completed = pending == 0
    notices = _notices(session, attempt)
    if completed:
        progress.complete_lesson(
            session, record, attempt.lesson_id, now, attempt.syllabus_version
        )  # commits
    else:
        session.commit()
    return RetakeResult(
        retake,
        question,
        response,
        correct,
        marked.feedback,
        next_question,
        pending,
        completed,
        notices,
        retake.waived_reason is not None,
    )


def _pending(session: Session, attempt: LessonQuizAttempt) -> list[PendingRetake]:
    retakes = session.scalars(
        select(Retake).where(Retake.lesson_quiz_attempt_id == attempt.id, Retake.done_at.is_(None))
    ).all()
    order = {qid: i for i, qid in enumerate(attempt.question_ids)}
    return [
        PendingRetake(r, _question(session, attempt, r.asked_question_ids[-1]))
        for r in sorted(retakes, key=lambda r: order.get(r.missed_question_id, len(order)))
    ]


def _question(session: Session, attempt: LessonQuizAttempt, question_id: str) -> Question:
    """A Question of the attempt's Stack."""
    return session.scalars(
        select(Question).where(Question.stack_id == attempt.stack_id, Question.id == question_id)
    ).one()


def _next_question(
    session: Session, original: Question, asked: Sequence[str], rng: random.Random
) -> str | None:
    """An active sibling, never the original. None means the requirement must be waived."""
    sibling = quiz.pick_sibling(_concept_questions(session, original), original.id, asked, rng)
    return sibling


def _reconcile(
    session: Session, attempt: LessonQuizAttempt, rng: random.Random, now: datetime
) -> None:
    """Resolve pending obsolete content while holding the attempt's serialization lock."""
    rows = session.scalars(
        select(Retake).where(Retake.lesson_quiz_attempt_id == attempt.id, Retake.done_at.is_(None))
    ).all()
    for row in rows:
        original = _question(session, attempt, row.missed_question_id)
        if original.retired_reason is not None:
            row.waived_reason = (
                f"Retake waived: the missed Question was retired. {original.retired_reason}"
            )
            row.done_at = now
            continue
        waiting = (
            _question(session, attempt, row.asked_question_ids[-1])
            if row.asked_question_ids
            else None
        )
        if waiting is not None and waiting.retired_reason is None:
            continue
        sibling = _next_question(session, original, row.asked_question_ids, rng)
        if sibling is None:
            row.waived_reason = "Retake waived: no active sibling remains on this Concept."
            row.done_at = now
        else:
            row.asked_question_ids = [*row.asked_question_ids, sibling]
            row.replacement_notice = (
                "The waiting Question was retired. Answer its active replacement; "
                "your old response was not scored."
            )
    session.flush()


def _notices(session: Session, attempt: LessonQuizAttempt) -> list[RetakeNotice]:
    rows = session.scalars(
        select(Retake)
        .where(Retake.lesson_quiz_attempt_id == attempt.id)
        .order_by(Retake.created_at, Retake.id)
    ).all()
    return [
        RetakeNotice(row.id, reason, row.waived_reason is not None)
        for row in rows
        if (reason := row.waived_reason or row.replacement_notice) is not None
    ]


def _concept_questions(session: Session, original: Question) -> Sequence[str]:
    """Permanent IDs of the Questions a Retake may ask on the original's Concept (the original
    may be among them): never a Retired Question."""
    return session.scalars(
        select(Question.id)
        .where(
            Question.concept_pk == original.concept_pk,
            Question.type.in_(RETAKE_TYPES),
            Question.retired_reason.is_(None),
        )
        .order_by(Question.position)
    ).all()
