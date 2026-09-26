import logging
import uuid

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
    retakes,
    review,
    reviews,
    schemas,
    updated_lessons,
)
from app.auth import TokenVerifier
from app.deps import (
    ActiveStack,
    ActiveStackInPath,
    AdminLearner,
    CurrentLearner,
    GraderDep,
    Now,
    QuizRandom,
    SessionDep,
    UnlockedLesson,
    VerifierDep,
    get_current_learner,
    open_daily_review,
)
from app.models import Learner, Question

# Everything except the health check: only a signed-in, invited Learner gets in (app/deps.py),
# and each request counts as using the app for the Daily Review (`open_daily_review`).
router = APIRouter(dependencies=[Depends(get_current_learner), Depends(open_daily_review)])


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
    stack_id: str, session: SessionDep, learner: CurrentLearner, _: ActiveStack, now: Now
) -> schemas.SyllabusOut:
    """The Week map: the current Syllabus's Weeks, each with its Lessons (and their states) and
    Milestones (and whether they're ticked), in Syllabus order, for the signed-in Learner.

    `daily_review` is today's Daily Review (null when nothing is owed today). While a round is
    pending, the Lesson it locks has `waiting_for_review`, so the page can say why.
    `removed_lessons` are the Learner's Completed Lessons that a Syllabus Update removed: no
    longer on the path, kept as history (#13). `streak` is the Learner's Streak (#11)."""
    syllabus = lessons.current_syllabus(session, stack_id)
    if syllabus is None:
        raise HTTPException(404, "Stack not found")
    tz = learner.time_zone
    states = progress.lesson_states(session, learner.id, stack_id, tz, now)
    waiting = progress.waiting_for_review(session, learner.id, stack_id, tz, now)
    today = None if tz is None else reviews.daily_review(session, learner.id, stack_id, tz, now)
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
                        waiting_for_review=lesson.id == waiting,
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
        daily_review=_daily_review(today) if today is not None and today.rounds else None,
        removed_lessons=[
            schemas.RemovedLessonOut(
                id=r.id, title=r.title, completed_at=r.completed_at, version=r.syllabus_version
            )
            for r in updated_lessons.removed_completed_lessons(session, learner.id, stack_id)
        ],
        streak=0 if tz is None else reviews.streak(session, learner.id, stack_id, tz, now),
    )


@router.get("/stacks/{stack_id}/lessons/{lesson_id}")
def get_lesson(
    stack_id: str,
    lesson_id: str,
    session: SessionDep,
    learner: CurrentLearner,
    _: ActiveStack,
    now: Now,
) -> schemas.LessonOut:
    """A Lesson page. Locked Lessons can be read too, so Learners may read ahead: only the
    Lesson Quiz is gated (`UnlockedLesson`)."""
    lesson = lessons.find_current_lesson(session, stack_id, lesson_id)
    if lesson is None:
        raise HTTPException(404, "Lesson not found")
    previous_id, next_id = lessons.neighbour_lesson_ids(session, lesson)
    tz = learner.time_zone
    return schemas.LessonOut(
        id=lesson.id,
        stack_id=stack_id,
        week=schemas.WeekRef.model_validate(lesson.week),
        title=lesson.title,
        topics=lesson.topics,
        exercise=lesson.exercise,
        minutes=lesson.minutes,
        materials=[schemas.MaterialOut.model_validate(m) for m in lesson.materials],
        state=progress.lesson_states(session, learner.id, stack_id, tz, now)[lesson.id],
        waiting_for_review=progress.waiting_for_review(session, learner.id, stack_id, tz, now)
        == lesson.id,
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
RETAKE_DONE = {
    "code": "retake_done",
    "message": "You've already answered this Retake correctly.",
}


def _quiz_question(q: Question) -> schemas.QuizQuestionOut:
    """A Question to answer: never its answer, Model Answer or Explanation."""
    return schemas.QuizQuestionOut(
        id=q.id,
        type="written" if q.type == "written" else "multiple_choice",
        prompt=q.prompt,
        choices=[schemas.ChoiceOut(id=c["id"], text=c["text"]) for c in q.choices or []],
    )


def _answered_question(
    q: Question, response: str | None, feedback: str | None
) -> schemas.AnsweredQuestionOut:
    """A Question after it was answered, with its answer, the grader's feedback (written),
    Explanation and Materials."""
    return schemas.AnsweredQuestionOut(
        id=q.id,
        type="written" if q.type == "written" else "multiple_choice",
        prompt=q.prompt,
        choices=[schemas.ChoiceOut(id=c["id"], text=c["text"]) for c in q.choices or []],
        response=response,
        feedback=feedback,
        answer=q.answer,
        model_answer=None if q.model_answer is None else schemas.ModelAnswerOut(**q.model_answer),
        explanation=q.explanation,
        materials=[schemas.MaterialOut.model_validate(m) for m in q.materials],
    )


def _retakes_out(pending: list[retakes.PendingRetake]) -> list[schemas.RetakeOut]:
    return [
        schemas.RetakeOut(
            id=p.retake.id,
            missed_question_id=p.retake.missed_question_id,
            question=_quiz_question(p.question),
        )
        for p in pending
    ]


def _answer_too_long(error: marking.AnswerTooLong) -> HTTPException:
    detail = {
        "code": "answer_too_long",
        "message": (
            f"Your answer to {error.question_id} is too long: "
            f"keep it under {grading.MAX_ANSWER_CHARS} characters."
        ),
    }
    return HTTPException(422, detail)


def _not_a_choice(error: marking.NotAChoice) -> HTTPException:
    detail = {
        "code": "not_a_choice",
        "message": f"That isn't one of the choices for {error.question_id}.",
    }
    return HTTPException(422, detail)


@router.post("/stacks/{stack_id}/lessons/{lesson_id}/quiz")
def start_lesson_quiz(
    lesson: UnlockedLesson,
    active: ActiveStackInPath,
    session: SessionDep,
    rng: QuizRandom,
    now: Now,
) -> schemas.LessonQuizOut:
    """Start a Lesson Quiz on the Learner's Unlocked Lesson, or resume the one they started and
    haven't submitted. The Questions come without their answers.

    The guard (`UnlockedLesson`) is final: the backend refuses a Locked Lesson's quiz whatever
    the browser shows. 409 `quiz_unavailable` if the Lesson's Question Bank has no Questions to
    draw; 409 `retakes_pending` (with the passed `attempt_id`) if the last attempt passed and
    its Retakes, not a new quiz, will complete the Lesson. After an attempt below the Pass Mark
    the new quiz avoids that attempt's Questions as far as the bank allows.
    """
    try:
        started = quizzes.start_lesson_quiz(session, active, lesson, rng, now)
    except quizzes.QuizUnavailable as error:
        raise HTTPException(409, QUIZ_UNAVAILABLE) from error
    except quizzes.RetakesPending as error:
        detail = {
            "code": "retakes_pending",
            "message": "Finish the Retakes of your Missed Questions to complete this Lesson.",
            "attempt_id": str(error.attempt_id),
        }
        raise HTTPException(409, detail) from error
    return schemas.LessonQuizOut(
        attempt_id=started.attempt.id,
        lesson_id=started.attempt.lesson_id,
        version=started.attempt.syllabus_version,
        pass_mark=PASS_MARK_PERCENT,
        max_answer_chars=grading.MAX_ANSWER_CHARS,
        questions=[_quiz_question(q) for q in started.questions],
    )


@router.post("/stacks/{stack_id}/lessons/{lesson_id}/quiz/{attempt_id}/answers")
def submit_lesson_quiz(
    lesson_id: str,
    attempt_id: str,
    body: schemas.LessonQuizAnswersIn,
    active: ActiveStackInPath,
    session: SessionDep,
    grader: GraderDep,
    rng: QuizRandom,
    now: Now,
) -> schemas.LessonQuizResultOut:
    """Submit a Lesson Quiz's answers and get its score, each Missed Question's answer,
    Explanation and Materials, and what comes next (`next_step`). Scoring is the server's:
    a pass with no Missed Question makes the Lesson a Completed Lesson and unlocks the next one;
    a pass with Missed Questions opens their Retakes; below the Pass Mark comes a fresh quiz.

    Not guarded by `UnlockedLesson`: a quiz already started can always be finished (#9's
    Pending Review Round). 404 for an attempt that isn't the Learner's; 409 `quiz_submitted`
    the second time; 422 `question_not_in_quiz`, `not_a_choice` or `answer_too_long` for
    answers that don't fit the quiz, and then nothing is recorded.

    Written answers are graded against their Model Answers (app/grading.py), and each result
    carries the grader's one-line `feedback`. 503 `grading_failed` when grading fails (a timeout,
    a CLI error, or no Claude Code CLI): nothing is recorded, the attempt stays open, and
    the Learner submits again without penalty.
    """
    try:
        attempt_uuid = uuid.UUID(attempt_id)
        result = quizzes.submit_lesson_quiz(
            session, active, lesson_id, attempt_uuid, body.answers, now, grader
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
        raise _not_a_choice(error) from error
    except marking.AnswerTooLong as error:
        raise _answer_too_long(error) from error
    except grading.GradingFailed as error:
        raise HTTPException(503, GRADING_FAILED) from error
    completed, pending = result.lesson_completed, []
    if result.score.passed and not completed:
        state = retakes.open_retakes(session, active, lesson_id, attempt_uuid, rng, now)
        completed, pending = state.lesson_completed, state.pending
    next_step: schemas.NextStep = (
        "fresh_quiz" if not result.score.passed else "completed" if completed else "retakes"
    )
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
        missed=[
            _answered_question(q, result.responses[q.id], result.feedback[q.id])
            for q in result.missed
        ],
        next_step=next_step,
        lesson_completed=completed,
        retakes=_retakes_out(pending),
    )


@router.get("/stacks/{stack_id}/lessons/{lesson_id}/quiz/{attempt_id}/retakes")
def get_retakes(
    lesson_id: str,
    attempt_id: str,
    active: ActiveStackInPath,
    session: SessionDep,
    rng: QuizRandom,
    now: Now,
) -> schemas.RetakesOut:
    """A submitted attempt's pending Retakes, each with the sibling Question to answer (without
    its answer). Where `retakes_pending` points. Empty for an attempt below the Pass Mark, or
    once the Lesson is Completed.

    Not guarded by `UnlockedLesson`, like submitting. 404 for an attempt that isn't the
    Learner's or isn't submitted.
    """
    try:
        state = retakes.open_retakes(session, active, lesson_id, uuid.UUID(attempt_id), rng, now)
    except (ValueError, retakes.RetakeNotFound) as error:
        raise HTTPException(404, "Lesson Quiz not found") from error
    return schemas.RetakesOut(
        attempt_id=state.attempt.id,
        lesson_id=state.attempt.lesson_id,
        lesson_completed=state.lesson_completed,
        max_answer_chars=grading.MAX_ANSWER_CHARS,
        retakes=_retakes_out(state.pending),
    )


@router.post("/stacks/{stack_id}/lessons/{lesson_id}/retakes/{retake_id}/answers")
def answer_retake(
    lesson_id: str,
    retake_id: str,
    body: schemas.RetakeAnswerIn,
    active: ActiveStackInPath,
    session: SessionDep,
    grader: GraderDep,
    rng: QuizRandom,
    now: Now,
) -> schemas.RetakeResultOut:
    """Answer a Retake's sibling Question: a choice ID, a written answer, or null. Wrong: its
    Explanation (and the grader's feedback, for a written one), and another sibling to try.
    Correct: the Retake is done; the last one done completes the Lesson and unlocks the next.

    Not guarded by `UnlockedLesson`: Retakes under way can always be finished. 404 for a
    Retake that isn't the Learner's; 409 `retake_done` once answered correctly; 422
    `not_a_choice` or `answer_too_long`; 503 `grading_failed` when a written answer can't be
    graded. In each of those nothing is recorded and the Learner can answer again.
    """
    try:
        result = retakes.answer_retake(
            session,
            active,
            lesson_id,
            uuid.UUID(retake_id),
            body.answer,
            grader,
            rng,
            now,
        )
    except (ValueError, retakes.RetakeNotFound) as error:
        raise HTTPException(404, "Retake not found") from error
    except retakes.RetakeDone as error:
        raise HTTPException(409, RETAKE_DONE) from error
    except marking.NotAChoice as error:
        raise _not_a_choice(error) from error
    except marking.AnswerTooLong as error:
        raise _answer_too_long(error) from error
    except grading.GradingFailed as error:
        raise HTTPException(503, GRADING_FAILED) from error
    return schemas.RetakeResultOut(
        retake_id=result.retake.id,
        correct=result.correct,
        question=_answered_question(result.question, result.response, result.feedback),
        next_question=None
        if result.next_question is None
        else _quiz_question(result.next_question),
        pending=result.pending,
        lesson_completed=result.lesson_completed,
    )


# --- Daily Review ----------------------------------------------------------------------------

REVIEW_ROUND_FINISHED = {
    "code": "review_round_finished",
    "message": "You've already answered every Question of this Review Round.",
}
REVIEW_ROUND_DROPPED = {
    "code": "review_round_dropped",
    "message": "This Review Round was from an earlier day and has been dropped.",
}
QUESTION_ANSWERED = {
    "code": "question_answered",
    "message": "You've already answered this Question in this Review Round.",
}


def _round_summary(view: reviews.RoundView) -> schemas.ReviewRoundSummaryOut:
    r = view.round
    return schemas.ReviewRoundSummaryOut(
        id=r.id,
        number=r.number,
        state=view.state,
        opened_at=r.opened_at,
        pending_at=review.pending_at(r.opened_at),
        finished_at=r.finished_at,
        answered=len(view.answers),
        total=len(view.questions),
    )


def _daily_review(today: reviews.DailyReview) -> schemas.DailyReviewOut:
    return schemas.DailyReviewOut(
        day=today.day,
        time_zone=today.time_zone,
        rounds=[_round_summary(r) for r in today.rounds],
        next_round_at=today.next_round_at,
    )


def _round(view: reviews.RoundView) -> schemas.ReviewRoundOut:
    return schemas.ReviewRoundOut(
        **_round_summary(view).model_dump(),
        max_answer_chars=grading.MAX_ANSWER_CHARS,
        remaining=[_quiz_question(q) for q in view.remaining],
        results=[
            schemas.ReviewResultOut(
                correct=bool(a.correct), question=_answered_question(q, a.response, a.feedback)
            )
            for q, a in view.answered
        ],
    )


def _time_zone(learner: Learner) -> str:
    assert learner.time_zone is not None, "ActiveStack means the Learner has onboarded"
    return learner.time_zone


@router.get("/stacks/{stack_id}/review")
def get_daily_review(
    active: ActiveStackInPath, learner: CurrentLearner, session: SessionDep, now: Now
) -> schemas.DailyReviewDetailOut:
    """Today's Daily Review on the Active Stack, in the Learner's time zone: its Review Rounds,
    and the round waiting to be answered (`current`) with its remaining Questions (without their
    answers) and the results so far. No rounds means nothing is owed today: the Learner has no
    Completed Lesson yet, or had none at their first use of the day.

    Round 1 opens on the first request of the Learner's day, and Rounds 2 and 3 on the first
    request once due, to any route (`open_daily_review`
    runs before this one). 409 `not_active_stack` for another Stack."""
    today = reviews.daily_review(
        session, active.learner_id, active.stack_id, _time_zone(learner), now
    )
    current = today.current
    return schemas.DailyReviewDetailOut(
        **_daily_review(today).model_dump(),
        current=None if current is None else _round(current),
    )


@router.post("/stacks/{stack_id}/review/rounds/{round_id}/answers")
def answer_review_question(
    round_id: str,
    body: schemas.ReviewAnswerIn,
    active: ActiveStackInPath,
    learner: CurrentLearner,
    session: SessionDep,
    grader: GraderDep,
    now: Now,
) -> schemas.ReviewAnswerOut:
    """Answer one Question of a Review Round of today: a choice ID, a written answer, or null.
    The result carries the Question's correct answer or Model Answer, the grader's feedback
    (written) and its Explanation, for the page to show after a miss. The last answer finishes
    the round, and a finished Pending Review Round unlocks the Unlocked Lesson again.

    404 for a round that isn't the Learner's; 409 `review_round_finished`,
    `review_round_dropped` (a round of an earlier day) or `question_answered` (each Question is
    answered once); 422 `question_not_in_round`, `not_a_choice` or `answer_too_long`; 503
    `grading_failed` when a written answer can't be graded. In each of those nothing is
    recorded.
    """
    try:
        result = reviews.answer_question(
            session,
            active,
            _time_zone(learner),
            uuid.UUID(round_id),
            body.question_id,
            body.answer,
            grader,
            now,
        )
    except (ValueError, reviews.RoundNotFound) as error:
        raise HTTPException(404, "Review Round not found") from error
    except reviews.RoundFinished as error:
        raise HTTPException(409, REVIEW_ROUND_FINISHED) from error
    except reviews.RoundDropped as error:
        raise HTTPException(409, REVIEW_ROUND_DROPPED) from error
    except reviews.QuestionAnswered as error:
        raise HTTPException(409, QUESTION_ANSWERED) from error
    except reviews.QuestionNotInRound as error:
        detail = {
            "code": "question_not_in_round",
            "message": f"Not a Question of this Review Round: {error.question_id}",
        }
        raise HTTPException(422, detail) from error
    except marking.NotAChoice as error:
        raise _not_a_choice(error) from error
    except marking.AnswerTooLong as error:
        raise _answer_too_long(error) from error
    except grading.GradingFailed as error:
        raise HTTPException(503, GRADING_FAILED) from error
    return schemas.ReviewAnswerOut(
        correct=result.correct,
        question=_answered_question(result.question, result.response, result.feedback),
        round=_round_summary(result.round),
    )


@router.put("/stacks/{stack_id}/milestones/{milestone_id}")
def tick_milestone(
    milestone_id: str,
    body: schemas.MilestoneTickIn,
    active: ActiveStackInPath,
    session: SessionDep,
    now: Now,
) -> schemas.MilestoneTickOut:
    """Tick or untick a Milestone of the Active Stack. Ticks never change any lock state."""
    if lessons.find_current_milestone(session, active.stack_id, milestone_id) is None:
        raise HTTPException(404, "Milestone not found")
    progress.set_milestone_ticked(session, active, milestone_id, body.ticked, now)
    return schemas.MilestoneTickOut(id=milestone_id, ticked=body.ticked)


def create_app(
    verifier: TokenVerifier | None = None, grader: grading.Grader | None = None
) -> FastAPI:
    """The API. Session tokens are checked by `verifier`, by default the one CLERK_* configures;
    written answers are graded by `grader`, by default the Claude Code CLI (CLAUDE_BIN)."""
    _configure_logging()
    app = FastAPI(title="Learning App API")
    app.state.verifier = verifier or TokenVerifier.from_config()
    app.state.grader = grader or grading.grader_from_config(config.CLAUDE_BIN)

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
