"""Taking a Lesson Quiz: starting an attempt, submitting its answers, and the answers recorded.

The rules (Pass Mark, scoring, drawing) are the plain functions in `app/quiz.py`; this module
stores what they decide.

- **Starting** draws the Questions tagged to the Lesson in the Stack's Question Bank, never a
  Retired Question, and records the Syllabus version current then, which a pass completes the
  Lesson in (#13). Starting again before submitting resumes the same attempt, so a reload never
  redraws. After an attempt below the Pass Mark, the fresh one
  avoids that attempt's Questions as far as the bank allows; after a pass whose Retakes are
  still pending, starting is refused (`RetakesPending`).
- **Submitting** marks the answers against the attempt's own Questions. A Question never
  changes (ADR-0004), so a quiz in progress when a new version is imported, or when one of its
  Questions is retired, finishes on the Questions it drew. Every
  Question drawn gets an `Answer` row, unanswered ones included. A pass with no Missed
  Question makes the Lesson a Completed Lesson (`progress.complete_lesson`); a pass with Missed
  Questions leaves it to their Retakes (`app/retakes.py`, which the caller opens next).
- **Missed Questions** are read back with `missed_questions` / `missed_question_ids`, the
  record Review uses (#9).

A Lesson Quiz is four multiple-choice and two written Questions (`quiz.draw_quiz`). Answers are
marked by `marking.mark_all`, which grades written ones with the injected `Grader` (#7). If
grading fails, submitting raises `GradingFailed` and records nothing: the attempt stays open,
so the Learner resubmits without penalty.
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
from app.grading import Grader
from app.marking import AnswerTooLong, GradingFailed, NotAChoice, mark_all
from app.models import Answer, LearnerStack, Lesson, LessonQuizAttempt, Question, Syllabus

LESSON_QUIZ = "lesson_quiz"
"""`Answer.context` for an answer given in a Lesson Quiz."""


class QuizUnavailable(Exception):
    """The Lesson's Question Bank has no Question the quiz can draw."""


class RetakesPending(Exception):
    """The Lesson's last attempt passed, and its Retakes are still pending: they, not a new
    quiz, complete the Lesson."""

    def __init__(self, attempt_id: uuid.UUID) -> None:
        super().__init__(str(attempt_id))
        self.attempt_id = attempt_id


class AttemptNotFound(Exception):
    """No such attempt for this Learner, Stack and Lesson."""


class AlreadySubmitted(Exception):
    pass


class QuestionNotInQuiz(Exception):
    def __init__(self, question_ids: Sequence[str]) -> None:
        super().__init__(", ".join(question_ids))
        self.question_ids = list(question_ids)


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
    feedback: dict[str, str | None]
    """The grader's line for each graded written answer; None for the others."""
    questions: list[Question]
    """The attempt's Questions, in the order they were asked."""
    responses: dict[str, str | None]
    """The Learner's response to each Question, None for unanswered."""
    lesson_completed: bool
    """True when the quiz passed with no Missed Question. A pass with Missed Questions
    completes the Lesson once every Retake is correct."""

    @property
    def missed(self) -> list[Question]:
        """The Missed Questions, in the order they were asked."""
        return [q for q in self.questions if self.correct[q.id] is False]


def start_lesson_quiz(
    session: Session, record: LearnerStack, lesson: Lesson, rng: random.Random, now: datetime
) -> StartedQuiz:
    """Start a Lesson Quiz on `lesson` (a Lesson of the current Syllabus the caller has checked
    is the Unlocked Lesson), or resume the Learner's unsubmitted attempt at it.

    Raises RetakesPending if the last attempt passed and waits for its Retakes, and
    QuizUnavailable if the bank has nothing to draw.
    """
    attempt = _open_attempt(session, record, lesson.id)
    if attempt is not None:
        return StartedQuiz(attempt, _questions(session, attempt))
    previous = _last_submitted_attempt(session, record, lesson.id)
    if previous is not None and previous.passed:
        # Only reachable while the Lesson isn't Completed yet: its Retakes are pending.
        raise RetakesPending(previous.id)

    bank = session.scalars(
        select(Question)
        .where(
            Question.stack_id == record.stack_id,
            Question.lesson_id == lesson.id,
            Question.retired_reason.is_(None),
        )
        .options(joinedload(Question.concept))
        .order_by(Question.position)
    ).all()
    drawn = quiz.draw_quiz(
        [quiz.BankQuestion(q.id, q.concept.id, q.type) for q in bank],
        rng,
        avoid=previous.question_ids if previous is not None else (),
    )
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
    grader: Grader,
) -> QuizResult:
    """Mark and record the answers to an attempt, keyed by Question ID. A Question left out, or
    answered with None, is a Missed Question. At or above the Pass Mark with no Missed Question
    the Lesson becomes a Completed Lesson; with Missed Questions, the caller opens their Retakes
    (`retakes.open_retakes`), which complete it.

    Raises AttemptNotFound, AlreadySubmitted, QuestionNotInQuiz, NotAChoice, AnswerTooLong or
    GradingFailed; nothing is recorded then and the attempt stays open. Written answers are
    graded while the attempt's row is locked, so a double submission can't grade twice.
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

    questions = _questions(session, attempt)
    try:
        marked = mark_all(questions, responses, grader)
    except (NotAChoice, AnswerTooLong, GradingFailed):
        session.rollback()  # releases the lock; nothing was written
        raise
    correct = {qid: m.correct for qid, m in marked.items()}
    for question_id, is_correct in correct.items():
        session.add(
            Answer(
                learner_id=record.learner_id,
                stack_id=record.stack_id,
                question_id=question_id,
                context=LESSON_QUIZ,
                lesson_quiz_attempt_id=attempt.id,
                response=responses.get(question_id),
                correct=is_correct,
                feedback=marked[question_id].feedback,
                answered_at=now,
            )
        )
    result = quiz.score(correct.values())
    attempt.submitted_at = now
    attempt.correct_count = result.correct
    attempt.passed = result.passed
    completed = result.passed and all(correct.values())
    if completed:
        progress.complete_lesson(
            session, record, lesson_id, now, attempt.syllabus_version
        )  # commits
    else:
        session.commit()  # a pass with Missed Questions waits for its Retakes
    answered = {q.id: responses.get(q.id) for q in questions}
    feedback = {qid: m.feedback for qid, m in marked.items()}
    return QuizResult(attempt, result, correct, feedback, questions, answered, completed)


def recorded_answers(session: Session, learner_id: int, stack_id: str) -> list[Answer]:
    """Every answer the Learner has given on the Stack, oldest first."""
    return list(
        session.scalars(
            select(Answer)
            .where(Answer.learner_id == learner_id, Answer.stack_id == stack_id)
            .order_by(Answer.answered_at, Answer.id)
        )
    )


@dataclass(frozen=True)
class MissedQuestion:
    """A Question the Learner has answered wrongly or left unanswered at least once, anywhere:
    a Lesson Quiz, a Retake (a wrong sibling is a Missed Question too) or Review."""

    question_id: str
    """Permanent ID."""
    first_missed_at: datetime
    last_missed_at: datetime


def missed_questions(session: Session, learner_id: int, stack_id: str) -> list[MissedQuestion]:
    """The Learner's Missed Questions on the Stack, first missed first. This is the record the
    Review draws on (#9). A later correct answer doesn't remove one: Review decides when a
    Missed Question leaves its queue (correct on three different Days since `last_missed_at`:
    `review.in_queue`, read by `reviews._sources`)."""
    rows = session.execute(
        select(Answer.question_id, Answer.answered_at)
        .where(
            Answer.learner_id == learner_id,
            Answer.stack_id == stack_id,
            Answer.correct.is_(False),
        )
        .order_by(Answer.answered_at, Answer.id)
    ).all()
    missed: dict[str, MissedQuestion] = {}
    for question_id, answered_at in rows:
        first = missed.get(question_id)
        missed[question_id] = MissedQuestion(
            question_id,
            first.first_missed_at if first else answered_at,
            answered_at,
        )
    return list(missed.values())


def missed_question_ids(session: Session, learner_id: int, stack_id: str) -> list[str]:
    """Permanent IDs of `missed_questions`, first missed first."""
    return [m.question_id for m in missed_questions(session, learner_id, stack_id)]


def _last_submitted_attempt(
    session: Session, record: LearnerStack, lesson_id: str
) -> LessonQuizAttempt | None:
    return session.scalar(
        select(LessonQuizAttempt)
        .where(
            LessonQuizAttempt.learner_id == record.learner_id,
            LessonQuizAttempt.stack_id == record.stack_id,
            LessonQuizAttempt.lesson_id == lesson_id,
            LessonQuizAttempt.submitted_at.is_not(None),
        )
        .order_by(LessonQuizAttempt.submitted_at.desc())
        .limit(1)
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
    """The attempt's Questions, in the order they are asked."""
    return questions_by_id(session, attempt.stack_id, attempt.question_ids)


def questions_by_id(session: Session, stack_id: str, question_ids: Sequence[str]) -> list[Question]:
    """Questions of the Stack's Question Bank, in the order of `question_ids`, retired or not."""
    rows = session.scalars(
        select(Question).where(Question.stack_id == stack_id, Question.id.in_(question_ids))
    ).all()
    by_id = {q.id: q for q in rows}
    return [by_id[qid] for qid in question_ids]
