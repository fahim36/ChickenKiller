"""Review (#9): drawing a set of Questions across the Learner's Active Stacks, and answering them
one at a time. The rules (what is due, in what order) are the plain functions in
`app/review.py`; this module gathers the Learner's data for them and stores the answers.

- **Sets aren't stored.** A set is the first `review.SET_SIZE` Questions of the Learner's queue,
  drawn fresh on every request (`review_set`), so drawing changes nothing and a reload draws
  the same set until something is answered. There is nothing to finish, resume or drop.
- **The queue's sources**, for each Active Stack (`_sources`), all from the Stack's Question
  Bank (`review_bank`):
  1. the Missed Questions (`quizzes.missed_questions`), with every correct answer to them;
  2. the new Questions of the Learner's Updated Lessons they haven't answered yet
     (`updated_lessons.updated_question_ids`, #13);
  3. spaced repeats: the Questions of Completed Lessons and of played Daily Challenges
     (`_played_challenge_question_ids`, empty until #17), each with when it was last answered.
- **Every Question Review can ask** comes from `review_bank`, both for drawing and for
  answering: the Stack's Question Bank without its Retired Questions (#15), which are never
  drawn nor accepted.
- **Answering** (`answer_question`) takes any Question that is in the Learner's queue right now,
  on one of their Active Stacks; anything else is refused (`NotInReview`), such as a Locked
  Lesson's Question or a repeat already answered today. It is marked by `marking.mark` like a
  Lesson Quiz: a written answer is graded against its Model Answer, and if grading fails
  nothing is recorded and the Learner answers again. Every answer is an `Answer` with
  `context='review'`, so a wrong one is a Missed Question too, and a right one counts towards
  a Missed Question leaving the queue.
- **Review never blocks anything.** Nothing here is read by the lock states.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import progress, quizzes, review, updated_lessons
from app.grading import Grader
from app.marking import AnswerTooLong, GradingFailed, NotAChoice, mark
from app.models import Answer, LearnerStack, Lesson, Question, Stack
from app.review import QuestionRef

REVIEW = "review"
"""`Answer.context` for an answer given in Review."""


class NotInReview(Exception):
    """The Question isn't in the Learner's Review queue right now."""

    def __init__(self, question_id: str) -> None:
        super().__init__(question_id)
        self.question_id = question_id


@dataclass(frozen=True)
class ReviewQuestion:
    """A Question of a Review set, and the Active Stack it is asked on. It includes the correct
    answer: never send that before the Learner answers."""

    stack: Stack
    question: Question


@dataclass(frozen=True)
class AnswerResult:
    question: Question
    response: str | None
    correct: bool
    feedback: str | None
    """The grader's one line, for a graded written answer."""


def review_bank(session: Session, stack_id: str) -> list[Question]:
    """Every Question Review can draw or accept on the Stack: its Question Bank, leaving out
    Retired Questions (ADR-0004), in Syllabus order (the current Syllabus's Lesson order, then
    Question Bank order; Questions tagged to no current Lesson last)."""
    current_pk = select(Stack.current_syllabus_pk).where(Stack.id == stack_id).scalar_subquery()
    return list(
        session.scalars(
            select(Question)
            .outerjoin(
                Lesson, (Lesson.syllabus_pk == current_pk) & (Lesson.id == Question.lesson_id)
            )
            .where(Question.stack_id == stack_id, Question.retired_reason.is_(None))
            .options(selectinload(Question.sources), selectinload(Question.material_links))
            .order_by(Lesson.position.nulls_last(), Question.position)
        )
    )


def review_set(
    session: Session, records: Sequence[LearnerStack], now: datetime
) -> list[ReviewQuestion]:
    """The Learner's Review set at `now` across `records` (their Active Stacks): up to
    `review.SET_SIZE` Questions, in the order they are asked. Empty when nothing is due."""
    banks = {r.stack_id: {q.id: q for q in review_bank(session, r.stack_id)} for r in records}
    stacks = {r.stack_id: r.stack for r in records}
    sources = [_sources(session, r, banks[r.stack_id]) for r in records]
    merged = review.ReviewSources(
        missed=[m for s in sources for m in s.missed],
        updated=[q for s in sources for q in s.updated],
        repeats=[q for s in sources for q in s.repeats],
    )
    picked = review.queue(merged, review.utc_day(now))[: review.SET_SIZE]
    return [
        ReviewQuestion(stacks[ref.stack_id], banks[ref.stack_id][ref.question_id]) for ref in picked
    ]


def answer_question(
    session: Session,
    record: LearnerStack,
    question_id: str,
    response: str | None,
    grader: Grader,
    now: datetime,
) -> AnswerResult:
    """Mark and record the answer to one Question of the Learner's Review queue on this Active
    Stack: a choice ID or a written answer. None (or a blank written answer) is unanswered, so
    wrong.

    Raises NotInReview, NotAChoice, AnswerTooLong or GradingFailed; nothing is recorded then.
    The Learner's record on the Stack is locked while a written answer is graded, so a double
    submission can't grade twice.
    """
    session.execute(
        select(LearnerStack.learner_id)
        .where(
            LearnerStack.learner_id == record.learner_id,
            LearnerStack.stack_id == record.stack_id,
        )
        .with_for_update()
    )
    bank = {q.id: q for q in review_bank(session, record.stack_id)}
    ref = QuestionRef(record.stack_id, question_id)
    if ref not in review.queue(_sources(session, record, bank), review.utc_day(now)):
        session.rollback()  # releases the lock
        raise NotInReview(question_id)

    question = bank[question_id]
    try:
        marked = mark(question, response, grader)
    except (NotAChoice, AnswerTooLong, GradingFailed):
        session.rollback()  # releases the lock; nothing was written
        raise
    session.add(
        Answer(
            learner_id=record.learner_id,
            stack_id=record.stack_id,
            question_id=question.id,
            context=REVIEW,
            response=response,
            correct=marked.correct,
            feedback=marked.feedback,
            answered_at=now,
        )
    )
    session.commit()
    return AnswerResult(question, response, marked.correct, marked.feedback)


def _sources(
    session: Session, record: LearnerStack, bank: dict[str, Question]
) -> review.ReviewSources:
    """The Review queue's sources on one Active Stack (`review.ReviewSources`), keeping only
    Questions of `bank` (`review_bank`)."""
    learner_id, stack_id = record.learner_id, record.stack_id
    correct_at: dict[str, list[datetime]] = {}
    last_answered: dict[str, datetime] = {}
    for question_id, correct, answered_at in session.execute(
        select(Answer.question_id, Answer.correct, Answer.answered_at).where(
            Answer.learner_id == learner_id, Answer.stack_id == stack_id
        )
    ):
        if correct:
            correct_at.setdefault(question_id, []).append(answered_at)
        last_answered[question_id] = max(answered_at, last_answered.get(question_id, answered_at))

    def ref(question_id: str) -> QuestionRef:
        return QuestionRef(stack_id, question_id)

    completed = progress.completed_lesson_ids(session, learner_id, stack_id)
    played = set(_played_challenge_question_ids(session, learner_id, stack_id))
    return review.ReviewSources(
        missed=[
            review.Missed(
                ref(m.question_id),
                m.first_missed_at,
                m.last_missed_at,
                correct_at.get(m.question_id, []),
            )
            for m in quizzes.missed_questions(session, learner_id, stack_id)
            if m.question_id in bank
        ],
        updated=[
            ref(q)
            for q in updated_lessons.updated_question_ids(session, learner_id, stack_id)
            if q in bank
        ],
        repeats=[
            review.Repeat(ref(q.id), last_answered.get(q.id))
            for q in bank.values()
            if q.lesson_id in completed or q.id in played
        ],
    )


def _played_challenge_question_ids(session: Session, learner_id: int, stack_id: str) -> list[str]:
    """The Questions of the Daily Challenges the Learner has played on the Stack: a source of
    spaced repeats. Empty until Daily Challenges exist (#17 fills it)."""
    return []
