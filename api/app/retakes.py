"""Retakes (#8): after a Lesson Quiz that met the Pass Mark with Missed Questions, each Missed
Question is retaken on a sibling Question (same Concept, never the original), and the Lesson
becomes a Completed Lesson only when every Retake is correct.

- **Opening** (`open_retakes`) makes one `Retake` per Missed Question of a passed attempt and
  asks its first sibling. It is idempotent: the submit route calls it right after submitting,
  and reading the Retakes calls it again, so an interrupted request never strands a Lesson.
- **Answering** (`answer_retake`) marks the sibling asked with `marking.mark`, the same rules
  as the Lesson Quiz: a written sibling is graded against its Model Answer (#7). Correct: that
  Retake is done, and the last one done completes the Lesson. Wrong: its Explanation (and the
  grader's feedback) is shown and another sibling is asked (`quiz.pick_sibling`: unused ones
  first, then cycling, never the original). If grading fails, nothing is recorded and the
  Learner answers again.
- Siblings come from the Stack's Question Bank, and are never Retired Questions.
- Every answer is an `Answer` with `context='retake'`, so a wrong sibling is a Missed Question
  too (`quizzes.missed_questions`).

Retakes are keyed by the Learner and the attempt, not guarded by `UnlockedLesson`, so Retakes
already under way can always be finished.

A sibling may be of either type, whatever the Missed Question's type: a missed multiple-choice
Question can be retaken on a written sibling and vice versa.
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

RETAKE_TYPES = ("multiple_choice", "written")
"""Question types a Retake may ask: both, since `marking.mark` grades written answers."""


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


@dataclass(frozen=True)
class RetakeResult:
    retake: Retake
    question: Question
    """The sibling just answered."""
    response: str | None
    correct: bool
    feedback: str | None
    """The grader's one line, for a graded written answer."""
    next_question: Question | None
    """Another sibling to try, after a wrong answer."""
    pending: int
    """Retakes of the attempt still waiting for a correct answer."""
    lesson_completed: bool


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
        return RetakeState(attempt, [], lesson_completed=False)

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
        sibling = quiz.pick_sibling(_concept_questions(session, original), original.id, [], rng)
        if sibling is None:
            continue  # a Concept with one Question: the content check rules this out
        session.execute(
            insert(Retake)
            .values(
                id=uuid.uuid4(),
                learner_id=record.learner_id,
                stack_id=record.stack_id,
                lesson_quiz_attempt_id=attempt.id,
                missed_question_id=question_id,
                asked_question_ids=[sibling],
                created_at=now,
            )
            .on_conflict_do_nothing()
        )

    pending = _pending(session, attempt)
    if pending:
        session.commit()
        return RetakeState(attempt, pending, lesson_completed=False)
    progress.complete_lesson(
        session, record, attempt.lesson_id, now, attempt.syllabus_version
    )  # commits
    return RetakeState(attempt, [], lesson_completed=True)


def answer_retake(
    session: Session,
    record: LearnerStack,
    lesson_id: str,
    retake_id: uuid.UUID,
    response: str | None,
    grader: Grader,
    rng: random.Random,
    now: datetime,
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
        .with_for_update(of=Retake)
    )
    if retake is None:
        raise RetakeNotFound(retake_id)
    if retake.done_at is not None:
        raise RetakeDone(retake_id)
    attempt = session.get_one(LessonQuizAttempt, retake.lesson_quiz_attempt_id)
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
        next_id = quiz.pick_sibling(
            _concept_questions(session, original), original.id, retake.asked_question_ids, rng
        )
        assert next_id is not None  # the Retake was opened, so a sibling exists
        retake.asked_question_ids = [*retake.asked_question_ids, next_id]
        next_question = _question(session, attempt, next_id)
    session.flush()

    pending = len(_pending(session, attempt))
    completed = pending == 0
    if completed:
        progress.complete_lesson(
            session, record, attempt.lesson_id, now, attempt.syllabus_version
        )  # commits
    else:
        session.commit()
    return RetakeResult(
        retake, question, response, correct, marked.feedback, next_question, pending, completed
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
