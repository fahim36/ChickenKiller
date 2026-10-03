import re
import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict, Field, field_validator

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


class ChallengesAheadOut(BaseModel):
    """How far ahead a Stack's Daily Challenges are written (#16): through `written_through`
    (null when none are), with `days_left` counted from today (UTC) to it, both included.
    `warning` when fewer than three Days are left."""

    stack_id: str
    stack_name: str
    written_through: date | None
    days_left: int
    warning: bool


# --- Lesson Quiz -----------------------------------------------------------------------------


QuestionType = Literal["multiple_choice", "multiple_select", "written"]
"""Multiple choice (one choice), multiple select (tick every correct choice) or written (legacy,
ADR-0008)."""

Response = str | list[str] | None
"""An answer to one Question: a choice ID (multiple choice), the list of choice IDs ticked
(multiple select; an empty list is unanswered), the written answer, or null for unanswered."""


class ChoiceOut(BaseModel):
    id: str
    text: str


class QuizQuestionOut(BaseModel):
    """A Question as the Learner sees it while answering: never its answer(s), Model Answer or
    Explanation. A written Question has no choices."""

    id: str
    type: QuestionType
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
    """The Learner's answers, by Question ID: a choice ID, the list of choice IDs ticked
    (multiple select), the written answer (at most `max_answer_chars`), or null for unanswered.
    A Question left out, no ticks, or a blank written answer is unanswered too."""

    answers: dict[str, Response]


class QuestionResultOut(BaseModel):
    id: str
    correct: bool
    feedback: str | None = None
    """The grader's one line on a graded written answer; null otherwise."""


class ModelAnswerOut(BaseModel):
    summary: str
    key_points: list[str]


class SourceOut(BaseModel):
    """Where a Question's content came from, for checking it (ADR-0004)."""

    url: str
    title: str
    publisher: str
    accessed: date
    claim: str
    """The claim the Question relies on."""


class AnsweredQuestionOut(BaseModel):
    """A Question the Learner has answered, with everything shown afterwards: their response,
    the correct answer (a choice ID), the correct choices (multiple select) or Model Answer, the
    Explanation, the Materials and the Sources. Only ever sent after the answer is submitted."""

    id: str
    type: QuestionType
    prompt: str
    choices: list[ChoiceOut]
    """Empty for a written Question."""
    response: str | None
    """The Learner's choice ID, the choice IDs they ticked comma-separated ("a,c", multiple
    select; see `selected`), or written answer; null for unanswered."""
    selected: list[str]
    """The choice IDs the Learner ticked, for multiple select; empty otherwise."""
    feedback: str | None
    """The grader's one line on a graded written answer; null otherwise."""
    answer: str | None
    """The correct choice ID, for multiple choice."""
    answers: list[str]
    """Every correct choice ID, for multiple select; empty otherwise."""
    model_answer: ModelAnswerOut | None
    """For a written Question."""
    explanation: str
    materials: list[MaterialOut]
    sources: list[SourceOut]
    """Every Source, in order: shown after the Explanation."""


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
    """A choice ID, the list of choice IDs ticked (multiple select), a written answer, or null
    for unanswered (which counts as wrong)."""

    answer: Response


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
    """The answer to one Question of a Review set, on its Stack: a choice ID, the list of choice
    IDs ticked (multiple select), a written answer, or null for unanswered (which counts as
    wrong)."""

    stack_id: str
    question_id: str
    answer: Response


class ReviewAnswerOut(BaseModel):
    """An answered Review Question. `question` carries the correct answer or Model Answer, the
    grader's feedback (written) and the Explanation, shown after a miss."""

    correct: bool
    question: AnsweredQuestionOut


# --- Daily Challenges ------------------------------------------------------------------------

ChallengeOutcome = Literal["correct", "wrong", "ungraded"]


class ReplacementOut(BaseModel):
    """The Question that replaces a Retired Question (#19). `challenge_number` / `challenge_label`
    name the first released Daily Challenge that asks it, which is where it links to; both are
    null while none does (an Upcoming Challenge is never named)."""

    question_id: str
    challenge_number: int | None
    challenge_label: str | None


class ChallengeQuestionOut(BaseModel):
    """A Question of a Daily Challenge. Until the Learner's first answer, `answered` is null and
    nothing about its answer is sent. A Retired Question can't be answered: it has no choices,
    and comes with `retired_reason` and, if it has one, its replacement (`replaced_by`).

    `outcome` is the first try's: "ungraded" when grading that written answer failed, which
    earns no point. A multiple-select Question is marked without grading, so it is never
    ungraded."""

    id: str
    type: QuestionType
    prompt: str
    choices: list[ChoiceOut]
    retired: bool
    retired_reason: str | None
    replaced_by: ReplacementOut | None
    outcome: ChallengeOutcome | None
    answered: AnsweredQuestionOut | None
    """The first answer, with the correct answer, Explanation, Sources and Materials."""


class ChallengeOut(BaseModel):
    """A released Daily Challenge as the Learner has played it. `label` is how it is named:
    "Agentic AI Engineer #40 · 26 Sep" (its number and UTC Day).

    `status` is "not_started", "in_progress" or "finished". `score` / `out_of` are set once
    finished: first tries that were correct, out of the Questions that could be answered (an
    ungraded one included). After that it can be replayed, which changes nothing."""

    number: int
    day: date
    label: str
    status: Literal["not_started", "in_progress", "finished"]
    score: int | None
    out_of: int | None
    result_card: str | None
    """Set once finished: the Result Card to share, "Agentic AI Engineer #40 · 26 Sep · 2/3
    ✅❌⬜", a mark per answered Question (✅ correct, ❌ wrong, ⬜ ungraded) and never the
    Questions or answers."""
    max_answer_chars: int
    """The longest written answer accepted."""
    questions: list[ChallengeQuestionOut]
    """In the order they are asked."""


class TodaysChallengeOut(BaseModel):
    """An Active Stack's Daily Challenge for today (`day`, UTC), or null when none is written
    for today, and the Learner's Streak on the Stack.

    `streak` counts the consecutive Days, back from today, whose Challenge the Learner finished
    on its Day. A Day with no Challenge is skipped; today's, until finished, doesn't break it."""

    stack_id: str
    stack_name: str
    day: date
    streak: int
    challenge: ChallengeOut | None


class ArchivedChallengeOut(BaseModel):
    """A released Daily Challenge in the Archive (#19), with how the Learner played it: `status`
    as in `ChallengeOut`, and the first play's `score` / `out_of` once finished."""

    number: int
    day: date
    label: str
    status: Literal["not_started", "in_progress", "finished"]
    score: int | None
    out_of: int | None


class ArchiveOut(BaseModel):
    """An Active Stack's Archive: every released Daily Challenge, back to #1, newest first. An
    Upcoming Challenge is never in it. `day` is today (UTC)."""

    stack_id: str
    stack_name: str
    day: date
    challenges: list[ArchivedChallengeOut]


class StackChallengeOut(BaseModel):
    """One released Daily Challenge of an Active Stack, from its Archive. `day` is today (UTC):
    a Challenge whose own Day it isn't is an Archive play, which never counts toward a Streak."""

    stack_id: str
    stack_name: str
    day: date
    challenge: ChallengeOut


class CatchUpStackOut(BaseModel):
    """One Active Stack's Catch-up: its past Daily Challenges the Learner hasn't finished, newest
    first, and how many (`count`)."""

    stack_id: str
    stack_name: str
    count: int
    challenges: list[ArchivedChallengeOut]


class CatchUpOut(BaseModel):
    """Catch-up across the Learner's Active Stacks, one entry each (`count` 0 when there's
    nothing to catch up on). Optional: it never blocks anything."""

    stacks: list[CatchUpStackOut]


class ChallengeAnswerIn(BaseModel):
    """The answer to one Question of a Daily Challenge: a choice ID, the list of choice IDs
    ticked (multiple select), a written answer, or null for unanswered (which counts as
    wrong)."""

    question_id: str
    answer: Response


class ChallengeAnswerOut(BaseModel):
    """A marked answer. `counted` is true only for the first answer to the Question, the one
    scored; a later one (after a grading failure, or in a replay) is marked for learning and
    changes nothing. `question` carries the result's details: the correct answer or Model
    Answer, the grader's feedback (written), the Explanation and every Source. `challenge` is
    the Challenge after this answer."""

    counted: bool
    outcome: ChallengeOutcome
    question: AnsweredQuestionOut
    challenge: ChallengeOut


# --- Settings: grading keys and access tokens -------------------------------------------------


class GradingKeyOut(BaseModel):
    """A saved LLM key as the Learner sees it: never the key, only its last four characters."""

    provider: str
    model: str
    key_hint: str
    updated_at: datetime


class GradingOut(BaseModel):
    """How the Learner's written answers are graded.

    `key` is their own saved key, if any. `grader` is what grades them: `own_key`, `admin_key`
    (they have none, and the Admin saved one), `server` (the Claude Code CLI on the API's
    machine) or `none` (they must save their own key first). `keys_enabled` is false when the
    server can't store keys (no LLM_KEY_SECRET). `own_key_required` is true when every Learner
    but the Admin is graded only with their own key (OWN_GRADING_KEY_REQUIRED)."""

    key: GradingKeyOut | None
    grader: Literal["own_key", "admin_key", "server", "none"]
    keys_enabled: bool
    default_model: str
    own_key_required: bool = False


class GradingKeyIn(BaseModel):
    provider: Literal["gemini", "nvidia"] = "gemini"
    api_key: str
    model: str | None = None


class AccessTokenOut(BaseModel):
    id: int
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None


class NewAccessTokenOut(AccessTokenOut):
    token: str
    """The token itself: shown this once."""


class AccessTokenIn(BaseModel):
    name: str = "Claude"


class DraftOut(BaseModel):
    id: int
    stack_id: str
    kind: Literal["questions", "challenge", "stack", "syllabus"]
    status: Literal["pending", "accepted", "rejected", "exported"]
    author_email: str
    note: str
    payload: dict[str, Any]
    created_at: datetime
    decided_at: datetime | None


class DraftDecisionIn(BaseModel):
    status: Literal["accepted", "rejected"]


class StackRequestIn(BaseModel):
    """A request for a new Stack (app/stack_builder.py)."""

    id: str = Field(max_length=80)
    name: str = Field(max_length=120)
    summary: str = Field(max_length=500)
    audience: str = Field("", max_length=500)
    weeks: int = 12
    notes: str = Field("", max_length=2000)


class LessonProgressOut(BaseModel):
    id: str
    title: str
    multiple_choice: int
    multiple_select: int
    ready: bool


class StackPlanOut(BaseModel):
    """Where a requested Stack stands: `plan` (no weekly plan yet), `questions` (its Lessons
    still need Questions) or `review` (the Admin accepts and exports the drafts)."""

    stack_id: str
    name: str
    requested_by: str
    request_status: Literal["pending", "accepted", "rejected", "exported"]
    weeks_wanted: int | None
    step: Literal["plan", "questions", "review"]
    next_step: str
    syllabus_draft: int | None
    syllabus_status: Literal["pending", "accepted", "rejected", "exported"] | None
    lessons: list[LessonProgressOut]
    lessons_ready: int
    thin_concepts: list[str]
