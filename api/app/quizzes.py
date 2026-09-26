"""Taking a Lesson Quiz: starting an attempt, submitting its answers, and the answers recorded.

The rules (Pass Mark, scoring, drawing) are the plain functions in `app/quiz.py`; this module
stores what they decide.

- **Starting** draws the Questions from the Lesson's Question Bank in the Stack's current
  Syllabus and pins the attempt to that version. Starting again before submitting resumes the
  same attempt, so a reload never redraws.
- **Submitting** marks the answers against the attempt's own Questions from its pinned version,
  so a quiz in progress when a new version is imported finishes on the old one (#13). Every
  Question drawn gets an `Answer` row, unanswered ones included, and a pass makes the Lesson a
  Completed Lesson (`progress.complete_lesson`).

#6 draws multiple-choice Questions only. #7 adds written ones: `_mark` grades them, and a grading
failure leaves `correct` null so the attempt can be resubmitted. #8 adds Retakes: a pass with
Missed Questions then waits for them instead of completing the Lesson here.
"""

import random
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import progress, quiz
from app.models import Answer, LearnerStack, Lesson, LessonQuizAttempt, Question, Syllabus

LESSON_QUIZ = "lesson_quiz"
"""`Answer.context` for an answer given in a Lesson Quiz."""


class QuizUnavailable(Exception):
    """The Lesson's Question Bank has no Question the quiz can draw."""


class AttemptNotFound(Exception):
    """No such attempt for this Learner, Stack and Lesson."""


class AlreadySubmitted(Exception):
    pass


class QuestionNotInQuiz(Exception):
    def __init__(self, question_ids: Sequence[str]) -> None:
        super().__init__(", ".join(question_ids))
        self.question_ids = list(question_ids)


class NotAChoice(Exception):
    def __init__(self, question_id: str) -> None:
        super().__init__(question_id)
        self.question_id = question_id


@dataclass(frozen=True)
class StartedQuiz:
    attempt: LessonQuizAttempt
    questions: list[Question]
    """In the order they are asked. They include the correct answers: never send those."""


@dataclass(frozen=True)
class QuizResult:
    attempt: LessonQuizAttempt
    score: quiz.Score
    correct: dict[str, bool]
    """Each Question's result, by permanent ID, in the order they were asked."""


def start_lesson_quiz(
    session: Session, record: LearnerStack, lesson: Lesson, rng: random.Random, now: datetime
) -> StartedQuiz:
    """Start a Lesson Quiz on `lesson` (a Lesson of the current Syllabus the caller has checked
    is the Unlocked Lesson), or resume the Learner's unsubmitted attempt at it."""
    attempt = _open_attempt(session, record, lesson.id)
    if attempt is not None:
        return StartedQuiz(attempt, _questions(session, attempt))

    bank = session.scalars(
        select(Question)
        .where(Question.lesson_pk == lesson.pk, Question.type == "multiple_choice")
        .options(joinedload(Question.concept))
        .order_by(Question.position)
    ).all()
    drawn = quiz.draw_questions([quiz.BankQuestion(q.id, q.concept.id) for q in bank], rng)
    if not drawn:
        raise QuizUnavailable(lesson.id)
    version = session.scalars(
        select(Syllabus.version).where(Syllabus.pk == lesson.syllabus_pk)
    ).one()
    attempt = LessonQuizAttempt(
        id=uuid.uuid4(),
        learner_id=record.learner_id,
        stack_id=record.stack_id,
        lesson_id=lesson.id,
        syllabus_version=version,
        question_ids=drawn,
        started_at=now,
    )
    session.add(attempt)
    try:
        session.commit()
    except IntegrityError:
        # Another request started this quiz first (one open attempt per Lesson): resume it.
        session.rollback()
        attempt = _open_attempt(session, record, lesson.id)
        if attempt is None:
            raise
        return StartedQuiz(attempt, _questions(session, attempt))
    by_id = {q.id: q for q in bank}
    return StartedQuiz(attempt, [by_id[qid] for qid in drawn])


def submit_lesson_quiz(
    session: Session,
    record: LearnerStack,
    lesson_id: str,
    attempt_id: uuid.UUID,
    responses: Mapping[str, str | None],
    now: datetime,
) -> QuizResult:
    """Mark and record the answers to an attempt, keyed by Question ID. A Question left out, or
    answered with None, is a Missed Question. At or above the Pass Mark the Lesson becomes a
    Completed Lesson.

    Raises AttemptNotFound, AlreadySubmitted, QuestionNotInQuiz or NotAChoice; nothing is
    recorded then.
    """
    attempt = session.scalar(
        select(LessonQuizAttempt)
        .where(
            LessonQuizAttempt.id == attempt_id,
            LessonQuizAttempt.learner_id == record.learner_id,
            LessonQuizAttempt.stack_id == record.stack_id,
            LessonQuizAttempt.lesson_id == lesson_id,
        )
        .with_for_update()
    )
    if attempt is None:
        raise AttemptNotFound(attempt_id)
    if attempt.submitted_at is not None:
        raise AlreadySubmitted(attempt_id)
    unknown = [qid for qid in responses if qid not in attempt.question_ids]
    if unknown:
        raise QuestionNotInQuiz(unknown)

    correct = {q.id: _mark(q, responses.get(q.id)) for q in _questions(session, attempt)}
    for question_id, is_correct in correct.items():
        session.add(
            Answer(
                learner_id=record.learner_id,
                stack_id=record.stack_id,
                question_id=question_id,
                syllabus_version=attempt.syllabus_version,
                context=LESSON_QUIZ,
                lesson_quiz_attempt_id=attempt.id,
                response=responses.get(question_id),
                correct=is_correct,
                answered_at=now,
            )
        )
    result = quiz.score(correct.values())
    attempt.submitted_at = now
    attempt.correct_count = result.correct
    attempt.passed = result.passed
    if result.passed:
        progress.complete_lesson(session, record, lesson_id, now)  # commits
    else:
        session.commit()
    return QuizResult(attempt, result, correct)


def recorded_answers(session: Session, learner_id: int, stack_id: str) -> list[Answer]:
    """Every answer the Learner has given on the Stack, oldest first."""
    return list(
        session.scalars(
            select(Answer)
            .where(Answer.learner_id == learner_id, Answer.stack_id == stack_id)
            .order_by(Answer.answered_at, Answer.id)
        )
    )


def _open_attempt(
    session: Session, record: LearnerStack, lesson_id: str
) -> LessonQuizAttempt | None:
    return session.scalar(
        select(LessonQuizAttempt).where(
            LessonQuizAttempt.learner_id == record.learner_id,
            LessonQuizAttempt.stack_id == record.stack_id,
            LessonQuizAttempt.lesson_id == lesson_id,
            LessonQuizAttempt.submitted_at.is_(None),
        )
    )


def _questions(session: Session, attempt: LessonQuizAttempt) -> list[Question]:
    """The attempt's Questions from its pinned Syllabus version, in the order they are asked."""
    rows = session.scalars(
        select(Question)
        .join(Syllabus, Syllabus.pk == Question.syllabus_pk)
        .where(
            Syllabus.stack_id == attempt.stack_id,
            Syllabus.version == attempt.syllabus_version,
            Question.id.in_(attempt.question_ids),
        )
    ).all()
    by_id = {q.id: q for q in rows}
    return [by_id[qid] for qid in attempt.question_ids]


def _mark(question: Question, response: str | None) -> bool:
    """Whether a response to a multiple-choice Question is correct. Raises NotAChoice for a
    response that isn't one of its choices."""
    if response is None:
        return False
    if response not in {c["id"] for c in question.choices or []}:
        raise NotAChoice(question.id)
    return response == question.answer
