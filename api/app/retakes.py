"""Retakes (#8): after a Lesson Quiz that met the Pass Mark with Missed Questions, each Missed
Question is retaken on a sibling Question (same Concept, never the original), and the Lesson
becomes a Completed Lesson only when every Retake is correct.

- **Opening** (`open_retakes`) makes one `Retake` per Missed Question of a passed attempt and
  asks its first sibling. It is idempotent: the submit route calls it right after submitting,
  and reading the Retakes calls it again, so an interrupted request never strands a Lesson.
- **Answering** (`answer_retake`) marks the sibling asked. Correct: that Retake is done, and
  the last one done completes the Lesson. Wrong: its Explanation is shown and another sibling
  is asked (`quiz.pick_sibling`: unused ones first, then cycling, never the original).
- Siblings come from the attempt's pinned Syllabus version, like the quiz itself (#13).
- Every answer is an `Answer` with `context='retake'`, so a wrong sibling is a Missed Question
  too (`quizzes.missed_questions`).

Retakes are keyed by the Learner and the attempt, not guarded by `UnlockedLesson`, so Retakes
already under way can be finished even if the Lesson becomes locked (#9's Pending Review Round).

Only multiple-choice siblings can be asked until #7 grades written answers (`RETAKE_TYPES` and
`_mark`). Until then a Missed Question whose Concept has no other multiple-choice Question gets
no Retake, and doesn't hold up the Lesson.
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
from app.models import Answer, LearnerStack, LessonQuizAttempt, Question, Retake, Syllabus
from app.quizzes import NotAChoice

RETAKE = "retake"
"""`Answer.context` for an answer given in a Retake."""

RETAKE_TYPES = ("multiple_choice",)
"""Question types a Retake may ask. #7 adds "written" once `_mark` can grade it."""


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
        original = _version_question(session, attempt, question_id)
        sibling = quiz.pick_sibling(_concept_questions(session, original), original.id, [], rng)
        if sibling is None:
            continue  # no sibling a Retake can ask yet (see RETAKE_TYPES)
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
    progress.complete_lesson(session, record, attempt.lesson_id, now)  # commits
    return RetakeState(attempt, [], lesson_completed=True)


def answer_retake(
    session: Session,
    record: LearnerStack,
    lesson_id: str,
    retake_id: uuid.UUID,
    response: str | None,
    rng: random.Random,
    now: datetime,
) -> RetakeResult:
    """Mark and record the answer to a Retake's waiting sibling. None is unanswered, so wrong.

    Raises RetakeNotFound, RetakeDone, or NotAChoice for a response that isn't one of the
    sibling's choices; nothing is recorded then.
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
    question = _version_question(session, attempt, retake.asked_question_ids[-1])
    correct = _mark(question, response)
    session.add(
        Answer(
            learner_id=record.learner_id,
            stack_id=record.stack_id,
            question_id=question.id,
            syllabus_version=attempt.syllabus_version,
            context=RETAKE,
            retake_id=retake.id,
            response=response,
            correct=correct,
            answered_at=now,
        )
    )

    next_question = None
    if correct:
        retake.done_at = now
    else:
        original = _version_question(session, attempt, retake.missed_question_id)
        next_id = quiz.pick_sibling(
            _concept_questions(session, original), original.id, retake.asked_question_ids, rng
        )
        assert next_id is not None  # the Retake was opened, so a sibling exists
        retake.asked_question_ids = [*retake.asked_question_ids, next_id]
        next_question = _version_question(session, attempt, next_id)
    session.flush()

    pending = len(_pending(session, attempt))
    completed = pending == 0
    if completed:
        progress.complete_lesson(session, record, attempt.lesson_id, now)  # commits
    else:
        session.commit()
    return RetakeResult(retake, question, response, correct, next_question, pending, completed)


def _mark(question: Question, response: str | None) -> bool:
    """Whether a Retake's response is correct. Multiple choice only for now: #7 swaps this for
    its `mark(question, response, grader)` and adds "written" to RETAKE_TYPES."""
    if response is None:
        return False
    if response not in {c["id"] for c in question.choices or []}:
        raise NotAChoice(question.id)
    return response == question.answer


def _pending(session: Session, attempt: LessonQuizAttempt) -> list[PendingRetake]:
    retakes = session.scalars(
        select(Retake).where(Retake.lesson_quiz_attempt_id == attempt.id, Retake.done_at.is_(None))
    ).all()
    order = {qid: i for i, qid in enumerate(attempt.question_ids)}
    return [
        PendingRetake(r, _version_question(session, attempt, r.asked_question_ids[-1]))
        for r in sorted(retakes, key=lambda r: order.get(r.missed_question_id, len(order)))
    ]


def _version_question(session: Session, attempt: LessonQuizAttempt, question_id: str) -> Question:
    """A Question from the attempt's pinned Syllabus version."""
    return session.scalars(
        select(Question)
        .join(Syllabus, Syllabus.pk == Question.syllabus_pk)
        .where(
            Syllabus.stack_id == attempt.stack_id,
            Syllabus.version == attempt.syllabus_version,
            Question.id == question_id,
        )
    ).one()


def _concept_questions(session: Session, original: Question) -> Sequence[str]:
    """Permanent IDs of the Questions a Retake may ask on the original's Concept, in the same
    version (the original among them)."""
    return session.scalars(
        select(Question.id)
        .where(Question.concept_pk == original.concept_pk, Question.type.in_(RETAKE_TYPES))
        .order_by(Question.position)
    ).all()
