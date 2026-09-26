import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, FastAPI, HTTPException

from app import (
    config,
    grading,
    learners,
    lessons,
    marking,
    onboarding,
    progress,
    quiz,
    quizzes,
    schemas,
)
from app.auth import TokenVerifier
from app.deps import (
    ActiveStack,
    ActiveStackInPath,
    AdminLearner,
    CurrentLearner,
    GraderDep,
    QuizRandom,
    SessionDep,
    UnlockedLesson,
    VerifierDep,
    get_current_learner,
)
from app.models import Learner

# Everything except the health check: only a signed-in, invited Learner gets in (app/deps.py).
router = APIRouter(dependencies=[Depends(get_current_learner)])


def _me(session: SessionDep, learner: Learner, verifier: VerifierDep) -> schemas.MeOut:
    record = onboarding.active_stack(session, learner)
    return schemas.MeOut(
        email=learner.email,
        is_admin=learners.is_admin(learner, verifier.settings.admin_emails),
        needs_onboarding=onboarding.needs_onboarding(learner),
        active_stack=None
        if record is None
        else schemas.ActiveStackOut(
            id=record.stack.id, name=record.stack.name, started_at=record.started_at
        ),
        time_zone=learner.time_zone,
    )


@router.get("/me")
def me(learner: CurrentLearner, session: SessionDep, verifier: VerifierDep) -> schemas.MeOut:
    return _me(session, learner, verifier)


@router.put("/me/settings")
def save_settings(
    body: schemas.SettingsIn, learner: CurrentLearner, session: SessionDep, verifier: VerifierDep
) -> schemas.MeOut:
    """Onboarding, and settings later: set the Active Stack and time zone."""
    try:
        onboarding.choose(session, learner, body.active_stack_id, body.time_zone)
    except onboarding.NotPublished as error:
        raise HTTPException(422, "Choose one of the published Stacks.") from error
    return _me(session, learner, verifier)


@router.get("/invitations")
def list_pending_invitations(_: AdminLearner, session: SessionDep) -> list[schemas.InvitationOut]:
    return [schemas.InvitationOut.model_validate(i) for i in learners.pending_invitations(session)]


@router.post("/invitations", status_code=201)
def invite(
    body: schemas.InvitationIn, _: AdminLearner, session: SessionDep
) -> schemas.InvitationOut:
    try:
        invitation = learners.invite(session, body.email)
    except learners.AlreadyInvited as error:
        raise HTTPException(409, f"{body.email} is already invited.") from error
    except learners.AlreadyALearner as error:
        raise HTTPException(409, f"{body.email} is already a Learner.") from error
    return schemas.InvitationOut.model_validate(invitation)


@router.get("/stacks")
def list_stacks(session: SessionDep) -> list[schemas.StackSummary]:
    return [
        schemas.StackSummary(
            id=s.id, name=s.name, summary=s.summary, version=s.current_syllabus.version
        )
        for s in lessons.list_stacks(session)
        if s.current_syllabus is not None
    ]


@router.get("/stacks/{stack_id}")
def get_week_map(
    stack_id: str, session: SessionDep, learner: CurrentLearner, _: ActiveStack
) -> schemas.SyllabusOut:
    """The Week map: the current Syllabus's Weeks, each with its Lessons (and their states) and
    Milestones (and whether they're ticked), in Syllabus order, for the signed-in Learner."""
    syllabus = lessons.current_syllabus(session, stack_id)
    if syllabus is None:
        raise HTTPException(404, "Stack not found")
    states = progress.lesson_states(session, learner.id, stack_id)
    ticked = progress.ticked_milestone_ids(session, learner.id, stack_id)
    stack = syllabus.stack
    return schemas.SyllabusOut(
        id=stack.id,
        name=stack.name,
        summary=stack.summary,
        version=syllabus.version,
        weeks=[
            schemas.WeekOut(
                id=week.id,
                number=week.number,
                title=week.title,
                goal=week.goal,
                deliverable=week.deliverable,
                lessons=[
                    schemas.LessonSummary(
                        id=lesson.id,
                        title=lesson.title,
                        minutes=lesson.minutes,
                        state=states[lesson.id],
                    )
                    for lesson in week.lessons
                ],
                milestones=[
                    schemas.MilestoneOut(
                        id=m.id,
                        title=m.title,
                        kind=m.kind,
                        minutes=m.minutes,
                        ticked=m.id in ticked,
                    )
                    for m in week.milestones
                ],
            )
            for week in syllabus.weeks
        ],
    )


@router.get("/stacks/{stack_id}/lessons/{lesson_id}")
def get_lesson(
    stack_id: str, lesson_id: str, session: SessionDep, learner: CurrentLearner, _: ActiveStack
) -> schemas.LessonOut:
    """A Lesson page. Locked Lessons can be read too, so Learners may read ahead: only the
    Lesson Quiz is gated (`UnlockedLesson`)."""
    lesson = lessons.find_current_lesson(session, stack_id, lesson_id)
    if lesson is None:
        raise HTTPException(404, "Lesson not found")
    previous_id, next_id = lessons.neighbour_lesson_ids(session, lesson)
    return schemas.LessonOut(
        id=lesson.id,
        stack_id=stack_id,
        week=schemas.WeekRef.model_validate(lesson.week),
        title=lesson.title,
        topics=lesson.topics,
        exercise=lesson.exercise,
        minutes=lesson.minutes,
        materials=[schemas.MaterialOut.model_validate(m) for m in lesson.materials],
        state=progress.lesson_states(session, learner.id, stack_id)[lesson.id],
        previous_lesson_id=previous_id,
        next_lesson_id=next_id,
    )


PASS_MARK_PERCENT = int(quiz.PASS_MARK * 100)

QUIZ_UNAVAILABLE = {
    "code": "quiz_unavailable",
    "message": "This Lesson has no Lesson Quiz yet.",
}
QUIZ_SUBMITTED = {
    "code": "quiz_submitted",
    "message": "This Lesson Quiz has already been submitted.",
}
GRADING_FAILED = {
    "code": "grading_failed",
    "message": (
        "Your written answers couldn't be graded just now. Nothing was counted: "
        "submit again in a moment."
    ),
}


@router.post("/stacks/{stack_id}/lessons/{lesson_id}/quiz")
def start_lesson_quiz(
    lesson: UnlockedLesson, active: ActiveStackInPath, session: SessionDep, rng: QuizRandom
) -> schemas.LessonQuizOut:
    """Start a Lesson Quiz on the Learner's Unlocked Lesson, or resume the one they started and
    haven't submitted. The Questions come without their answers.

    The guard (`UnlockedLesson`) is final: the backend refuses a Locked Lesson's quiz whatever
    the browser shows. 409 `quiz_unavailable` if the Lesson's Question Bank has no Questions to
    draw.
    """
    try:
        started = quizzes.start_lesson_quiz(session, active, lesson, rng, datetime.now(UTC))
    except quizzes.QuizUnavailable as error:
        raise HTTPException(409, QUIZ_UNAVAILABLE) from error
    return schemas.LessonQuizOut(
        attempt_id=started.attempt.id,
        lesson_id=started.attempt.lesson_id,
        version=started.attempt.syllabus_version,
        pass_mark=PASS_MARK_PERCENT,
        max_answer_chars=grading.MAX_ANSWER_CHARS,
        questions=[
            schemas.QuizQuestionOut(
                id=q.id,
                type="written" if q.type == "written" else "multiple_choice",
                prompt=q.prompt,
                choices=[schemas.ChoiceOut(id=c["id"], text=c["text"]) for c in q.choices or []],
            )
            for q in started.questions
        ],
    )


@router.post("/stacks/{stack_id}/lessons/{lesson_id}/quiz/{attempt_id}/answers")
def submit_lesson_quiz(
    lesson_id: str,
    attempt_id: str,
    body: schemas.LessonQuizAnswersIn,
    active: ActiveStackInPath,
    session: SessionDep,
    grader: GraderDep,
) -> schemas.LessonQuizResultOut:
    """Submit a Lesson Quiz's answers and get its score. Scoring is the server's: a pass makes
    the Lesson a Completed Lesson and unlocks the next one.

    Not guarded by `UnlockedLesson`: a quiz already started can always be finished (#9's
    Pending Review Round). 404 for an attempt that isn't the Learner's; 409 `quiz_submitted`
    the second time; 422 `question_not_in_quiz`, `not_a_choice` or `answer_too_long` for
    answers that don't fit the quiz, and then nothing is recorded.

    Written answers are graded against their Model Answers (app/grading.py), and each result
    carries the grader's one-line `feedback`. 503 `grading_failed` when grading fails (a timeout,
    an API error, or no ANTHROPIC_API_KEY): nothing is recorded, the attempt stays open, and
    the Learner submits again without penalty.
    """
    try:
        attempt_uuid = uuid.UUID(attempt_id)
        result = quizzes.submit_lesson_quiz(
            session, active, lesson_id, attempt_uuid, body.answers, datetime.now(UTC), grader
        )
    except (ValueError, quizzes.AttemptNotFound) as error:
        raise HTTPException(404, "Lesson Quiz not found") from error
    except quizzes.AlreadySubmitted as error:
        raise HTTPException(409, QUIZ_SUBMITTED) from error
    except quizzes.QuestionNotInQuiz as error:
        detail = {
            "code": "question_not_in_quiz",
            "message": f"Not a Question of this quiz: {', '.join(error.question_ids)}",
        }
        raise HTTPException(422, detail) from error
    except marking.NotAChoice as error:
        detail = {
            "code": "not_a_choice",
            "message": f"That isn't one of the choices for {error.question_id}.",
        }
        raise HTTPException(422, detail) from error
    except marking.AnswerTooLong as error:
        detail = {
            "code": "answer_too_long",
            "message": (
                f"Your answer to {error.question_id} is too long: "
                f"keep it under {grading.MAX_ANSWER_CHARS} characters."
            ),
        }
        raise HTTPException(422, detail) from error
    except grading.GradingFailed as error:
        raise HTTPException(503, GRADING_FAILED) from error
    return schemas.LessonQuizResultOut(
        attempt_id=result.attempt.id,
        lesson_id=result.attempt.lesson_id,
        correct=result.score.correct,
        total=result.score.total,
        percent=result.score.percent,
        passed=result.score.passed,
        pass_mark=PASS_MARK_PERCENT,
        questions=[
            schemas.QuestionResultOut(id=qid, correct=ok, feedback=result.feedback[qid])
            for qid, ok in result.correct.items()
        ],
    )


@router.put("/stacks/{stack_id}/milestones/{milestone_id}")
def tick_milestone(
    milestone_id: str,
    body: schemas.MilestoneTickIn,
    active: ActiveStackInPath,
    session: SessionDep,
) -> schemas.MilestoneTickOut:
    """Tick or untick a Milestone of the Active Stack. Ticks never change any lock state."""
    if lessons.find_current_milestone(session, active.stack_id, milestone_id) is None:
        raise HTTPException(404, "Milestone not found")
    progress.set_milestone_ticked(session, active, milestone_id, body.ticked, datetime.now(UTC))
    return schemas.MilestoneTickOut(id=milestone_id, ticked=body.ticked)


def create_app(
    verifier: TokenVerifier | None = None, grader: grading.Grader | None = None
) -> FastAPI:
    """The API. Session tokens are checked by `verifier`, by default the one CLERK_* configures;
    written answers are graded by `grader`, by default Claude with ANTHROPIC_API_KEY."""
    _configure_logging()
    app = FastAPI(title="Learning App API")
    app.state.verifier = verifier or TokenVerifier.from_config()
    app.state.grader = grader or grading.grader_from_config(config.ANTHROPIC_API_KEY)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app


def _configure_logging() -> None:
    """Send the app's own INFO logs (such as each grading call's cost) to stderr, next to
    uvicorn's."""
    logger = logging.getLogger("app")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)


app = create_app()
