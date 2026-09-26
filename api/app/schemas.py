import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict, field_validator

from app.unlocking import LessonState


class BaseModel(_BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StackSummary(BaseModel):
    id: str
    name: str
    summary: str
    version: str


class MaterialOut(BaseModel):
    id: str
    title: str
    url: str
    type: str


class LessonSummary(BaseModel):
    """A Lesson on the Week map, with its state for the signed-in Learner."""

    id: str
    title: str
    minutes: int
    state: LessonState


class MilestoneOut(BaseModel):
    """A Milestone on the Week map, and whether the signed-in Learner has ticked it."""

    id: str
    title: str
    kind: str
    minutes: int
    ticked: bool


class MilestoneTickIn(BaseModel):
    ticked: bool


class MilestoneTickOut(BaseModel):
    id: str
    ticked: bool


class WeekOut(BaseModel):
    """A Week of the Week map: its Lessons and Milestones in Syllabus order."""

    id: str
    number: int
    title: str
    goal: str
    deliverable: str
    lessons: list[LessonSummary]
    milestones: list[MilestoneOut]


class RemovedLessonOut(BaseModel):
    """A Completed Lesson that the current Syllabus no longer has: history only (#13)."""

    id: str
    title: str
    """As it was in the version the Learner completed it in."""
    completed_at: datetime
    version: str
    """The version the Learner completed it in."""


class SyllabusOut(StackSummary):
    weeks: list[WeekOut]
    removed_lessons: list[RemovedLessonOut] = []
    """The Learner's Completed Lessons that a Syllabus Update removed, first completed first."""


class WeekRef(BaseModel):
    id: str
    number: int
    title: str


class LessonOut(BaseModel):
    id: str
    stack_id: str
    week: WeekRef
    title: str
    topics: list[str]
    exercise: str | None
    minutes: int
    materials: list[MaterialOut]
    state: LessonState
    previous_lesson_id: str | None
    next_lesson_id: str | None


class ActiveStackOut(BaseModel):
    """One of the Learner's Active Stacks, and when they first started studying it."""

    id: str
    name: str
    started_at: datetime


class MeOut(BaseModel):
    """The signed-in Learner. Admin-only screens check `is_admin`.

    `needs_onboarding` is true until the Learner has activated at least one Stack.
    `active_stacks` are the first started first.
    """

    email: str
    is_admin: bool
    needs_onboarding: bool
    active_stacks: list[ActiveStackOut]


class ActiveStacksIn(BaseModel):
    """What onboarding sets, and settings change: the Learner's Active Stacks, all of them. A
    Stack left out is deactivated, with its progress kept."""

    stack_ids: list[str]


# Deliberately loose: Clerk verifies the address when the person signs up.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InvitationIn(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _is_an_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL.match(value):
            raise ValueError("Enter an email address, such as name@example.com")
        return value


class InvitationOut(BaseModel):
    email: str
    invited_at: datetime


# --- Lesson Quiz -----------------------------------------------------------------------------


class ChoiceOut(BaseModel):
    id: str
    text: str


class QuizQuestionOut(BaseModel):
    """A Question as the Learner sees it while answering: never its answer, Model Answer or
    Explanation. A written Question has no choices."""

    id: str
    type: Literal["multiple_choice", "written"]
    prompt: str
    choices: list[ChoiceOut]


class LessonQuizOut(BaseModel):
    """A started (or resumed) Lesson Quiz. `attempt_id` names it when submitting."""

    attempt_id: uuid.UUID
    lesson_id: str
    version: str
    pass_mark: int
    """As a percentage."""
    max_answer_chars: int
    """The longest written answer accepted."""
    questions: list[QuizQuestionOut]


class LessonQuizAnswersIn(BaseModel):
    """The Learner's answers, by Question ID: a choice ID, the written answer (at most
    `max_answer_chars`), or null for unanswered. A Question left out, or a blank written answer,
    is unanswered too."""

    answers: dict[str, str | None]


class QuestionResultOut(BaseModel):
    id: str
    correct: bool
    feedback: str | None = None
    """The grader's one line on a graded written answer; null otherwise."""


class ModelAnswerOut(BaseModel):
    summary: str
    key_points: list[str]


class AnsweredQuestionOut(BaseModel):
    """A Question the Learner has answered, with everything shown afterwards: their response,
    the correct answer (a choice ID) or Model Answer, the Explanation and the Materials. Only
    ever sent after the answer is submitted."""

    id: str
    type: Literal["multiple_choice", "written"]
    prompt: str
    choices: list[ChoiceOut]
    """Empty for a written Question."""
    response: str | None
    """The Learner's choice ID or written answer; null for unanswered."""
    feedback: str | None
    """The grader's one line on a graded written answer; null otherwise."""
    answer: str | None
    """The correct choice ID, for multiple choice."""
    model_answer: ModelAnswerOut | None
    """For a written Question."""
    explanation: str
    materials: list[MaterialOut]


class RetakeOut(BaseModel):
    """A pending Retake: the sibling Question to answer for one Missed Question."""

    id: uuid.UUID
    missed_question_id: str
    question: QuizQuestionOut


NextStep = Literal["completed", "retakes", "fresh_quiz"]


class LessonQuizResultOut(BaseModel):
    """A submitted Lesson Quiz's score and what comes next.

    - `passed` means it met the Pass Mark. With no Missed Question that made the Lesson a
      Completed Lesson (`next_step` "completed"); with Missed Questions the Lesson waits for
      `retakes` ("retakes").
    - Below the Pass Mark (`next_step` "fresh_quiz") the Learner reads the Explanations and
      takes a fresh Lesson Quiz.
    - `missed` details each Missed Question, in the order asked.
    """

    attempt_id: uuid.UUID
    lesson_id: str
    correct: int
    total: int
    percent: int
    passed: bool
    pass_mark: int
    questions: list[QuestionResultOut]
    """In the order they were asked."""
    missed: list[AnsweredQuestionOut]
    next_step: NextStep
    lesson_completed: bool
    retakes: list[RetakeOut]
    """Pending Retakes, in the order their Missed Questions were asked."""


class RetakesOut(BaseModel):
    """A passed attempt's pending Retakes. Empty once `lesson_completed`."""

    attempt_id: uuid.UUID
    lesson_id: str
    lesson_completed: bool
    max_answer_chars: int
    """The longest written answer accepted."""
    retakes: list[RetakeOut]


class RetakeAnswerIn(BaseModel):
    """A choice ID, or null for unanswered (which counts as wrong)."""

    answer: str | None


class RetakeResultOut(BaseModel):
    """An answered Retake. Wrong: `question` shows its Explanation and `next_question` is
    another sibling to try. Correct: the Retake is done, and when `pending` reaches 0 the
    Lesson is a Completed Lesson and the next one is Unlocked."""

    retake_id: uuid.UUID
    correct: bool
    question: AnsweredQuestionOut
    next_question: QuizQuestionOut | None
    pending: int
    lesson_completed: bool


# --- Review ----------------------------------------------------------------------------------


class ReviewQuestionOut(QuizQuestionOut):
    """A Question of a Review set, without its answer, and the Active Stack it is asked on.
    Answer it on that Stack."""

    stack_id: str
    stack_name: str


class ReviewSetOut(BaseModel):
    """A Review set: up to `size` Questions across the Learner's Active Stacks, asked one at a
    time in order. Missed Questions come first, then Updated Lessons' new Questions, then
    spaced repeats. Empty when nothing is due. Sets aren't stored: asking again draws the next
    one."""

    size: int
    max_answer_chars: int
    """The longest written answer accepted."""
    questions: list[ReviewQuestionOut]


class ReviewAnswerIn(BaseModel):
    """The answer to one Question of a Review set, on its Stack: a choice ID, a written answer,
    or null for unanswered (which counts as wrong)."""

    stack_id: str
    question_id: str
    answer: str | None


class ReviewAnswerOut(BaseModel):
    """An answered Review Question. `question` carries the correct answer or Model Answer, the
    grader's feedback (written) and the Explanation, shown after a miss."""

    correct: bool
    question: AnsweredQuestionOut
