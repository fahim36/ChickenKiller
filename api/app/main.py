import logging
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import (
    access_tokens,
    challenges,
    config,
    grading,
    learners,
    lessons,
    llm_keys,
    marking,
    mcp_server,
    onboarding,
    progress,
    quiz,
    quizzes,
    retakes,
    review,
    reviews,
    schemas,
    stack_builder,
    updated_lessons,
)
from app.auth import TokenVerifier
from app.db import SessionLocal
from app.deps import (
    ONBOARDING_NEEDED,
    ActiveStackInPath,
    AdminLearner,
    CurrentLearner,
    GraderDep,
    KeyBoxDep,
    Now,
    QuizRandom,
    SessionDep,
    UnlockedLesson,
    VerifierDep,
    get_active_stack_in_path,
    get_current_learner,
    get_now,
)
from app.models import ContentDraft, Learner, Question

# Everything except the health check: only a signed-in, invited Learner gets in (app/deps.py).
router = APIRouter(dependencies=[Depends(get_current_learner)])


def _me(session: SessionDep, learner: Learner, verifier: VerifierDep) -> schemas.MeOut:
    active = onboarding.active_stacks(session, learner)
    return schemas.MeOut(
        email=learner.email,
        is_admin=learners.is_admin(learner, verifier.settings.admin_emails),
        needs_onboarding=not active,
        active_stacks=[
            schemas.ActiveStackOut(id=r.stack.id, name=r.stack.name, started_at=r.started_at)
            for r in active
        ],
    )


@router.get("/me")
def me(learner: CurrentLearner, session: SessionDep, verifier: VerifierDep) -> schemas.MeOut:
    return _me(session, learner, verifier)


@router.put("/me/active-stacks")
def save_active_stacks(
    body: schemas.ActiveStacksIn,
    learner: CurrentLearner,
    session: SessionDep,
    verifier: VerifierDep,
    now: Now,
) -> schemas.MeOut:
    """Onboarding, and settings later: make `stack_ids` the Learner's Active Stacks. A Stack
    left out is deactivated and keeps its progress; activating it again resumes it.

    422 when no Stack is picked (so the last Active Stack can't be deactivated on its own), or
    for a Stack that isn't published (unless it is already Active); nothing changes then."""
    try:
        onboarding.set_active_stacks(session, learner, body.stack_ids, now)
    except onboarding.NoStack as error:
        raise HTTPException(422, "Pick at least one Stack.") from error
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


@router.get("/admin/challenges")
def get_challenges_ahead(
    _: AdminLearner, session: SessionDep, now: Now
) -> list[schemas.ChallengesAheadOut]:
    """How far ahead each Stack's Daily Challenges are written, by Stack name, from today (UTC):
    "Challenges written through <date> (<n> Days left)", warning below three Days. Only counts:
    an Upcoming Challenge's Questions are never sent."""
    return [
        schemas.ChallengesAheadOut(
            stack_id=row.stack.id,
            stack_name=row.stack.name,
            written_through=row.ahead.written_through,
            days_left=row.ahead.days_left,
            warning=row.ahead.warning,
        )
        for row in challenges.challenges_ahead(session, now.astimezone(UTC).date())
    ]


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
    stack_id: str, session: SessionDep, learner: CurrentLearner, _: ActiveStackInPath
) -> schemas.SyllabusOut:
    """The Week map: the current Syllabus's Weeks, each with its Lessons (and their states) and
    Milestones (and whether they're ticked), in Syllabus order, for the signed-in Learner.
    Lesson states follow from Completed Lessons only; Milestone ticks never change them.

    `removed_lessons` are the Learner's Completed Lessons that a Syllabus Update removed: no
    longer on the path, kept as history (#13)."""
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
        removed_lessons=[
            schemas.RemovedLessonOut(
                id=r.id, title=r.title, completed_at=r.completed_at, version=r.syllabus_version
            )
            for r in updated_lessons.removed_completed_lessons(session, learner.id, stack_id)
        ],
    )


@router.get("/stacks/{stack_id}/lessons/{lesson_id}")
def get_lesson(
    stack_id: str,
    lesson_id: str,
    session: SessionDep,
    learner: CurrentLearner,
    _: ActiveStackInPath,
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
    Explanation, Materials and Sources."""
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
        sources=[schemas.SourceOut.model_validate(s) for s in q.sources],
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
    haven't submitted. The Questions come without their answers. It skips Questions the
    Learner has already seen, anywhere, as far as the Question Bank allows.

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
    Explanation, Sources and Materials, and what comes next (`next_step`). Scoring is the server's:
    a pass with no Missed Question makes the Lesson a Completed Lesson and unlocks the next one;
    a pass with Missed Questions opens their Retakes; below the Pass Mark comes a fresh quiz.

    Not guarded by `UnlockedLesson`: a quiz already started can always be finished. 404 for an
    attempt that isn't the Learner's; 409 `quiz_submitted` the second time; 422
    `question_not_in_quiz`, `not_a_choice` or `answer_too_long` for answers that don't fit the
    quiz, and then nothing is recorded.

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


# --- Daily Challenges ------------------------------------------------------------------------

QUESTION_RETIRED = {
    "code": "question_retired",
    "message": "This Question was retired, so it can't be answered. It isn't scored.",
}
CHALLENGE_GRADING_FAILED = {
    "code": "grading_failed",
    "message": "Your answer couldn't be graded just now. Nothing was counted: submit again.",
}


def challenge_label(stack_name: str, number: int, day: date) -> str:
    """How a Daily Challenge is named, with its number and UTC Day: "Agentic AI Engineer #40 ·
    26 Sep" (ADR-0005)."""
    return f"{stack_name} #{number} · {day.day} {_MONTHS[day.month - 1]}"


# Not `%b`, which follows the server's locale.
_MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def _challenge_out(stack_name: str, state: challenges.ChallengeState) -> schemas.ChallengeOut:
    """A Challenge as the Learner has played it: each Question's answer, Explanation and Sources
    only once it has a first answer."""
    c, play = state.challenge, state.play
    finished = play is not None and play.finished_at is not None
    label = challenge_label(stack_name, c.number, c.day)
    return schemas.ChallengeOut(
        number=c.number,
        day=c.day,
        label=label,
        status=state.status,
        score=play.score if finished and play else None,
        out_of=play.out_of if finished and play else None,
        result_card=challenges.result_card(label, state),
        max_answer_chars=grading.MAX_ANSWER_CHARS,
        questions=[_challenge_question(stack_name, q) for q in state.questions],
    )


def _replacement(
    stack_name: str, replacement: challenges.Replacement | None
) -> schemas.ReplacementOut | None:
    if replacement is None:
        return None
    c = replacement.challenge
    return schemas.ReplacementOut(
        question_id=replacement.question_id,
        challenge_number=None if c is None else c.number,
        challenge_label=None if c is None else challenge_label(stack_name, c.number, c.day),
    )


def _archived(
    stack_name: str, archived: challenges.ArchivedChallenge
) -> schemas.ArchivedChallengeOut:
    c, play = archived.challenge, archived.play
    finished = play is not None and play.finished_at is not None
    return schemas.ArchivedChallengeOut(
        number=c.number,
        day=c.day,
        label=challenge_label(stack_name, c.number, c.day),
        status=archived.status,
        score=play.score if finished and play else None,
        out_of=play.out_of if finished and play else None,
    )


def _challenge_question(
    stack_name: str, asked: challenges.ChallengeQuestion
) -> schemas.ChallengeQuestionOut:
    q, first = asked.question, asked.first_try
    unanswerable = q.retired and first is None
    return schemas.ChallengeQuestionOut(
        id=q.id,
        type="written" if q.type == "written" else "multiple_choice",
        prompt=q.prompt,
        choices=[]
        if unanswerable
        else [schemas.ChoiceOut(id=c["id"], text=c["text"]) for c in q.choices or []],
        retired=q.retired,
        retired_reason=q.retired_reason,
        replaced_by=_replacement(stack_name, asked.replacement),
        outcome=None if first is None else challenges.outcome(first.correct),
        answered=None if first is None else _answered_question(q, first.response, first.feedback),
    )


@router.get("/stacks/{stack_id}/challenges/today")
def get_todays_challenge(
    active: ActiveStackInPath, session: SessionDep, now: Now
) -> schemas.TodaysChallengeOut:
    """This Active Stack's Daily Challenge for today (UTC): the one dated today, released at
    00:00 UTC, the same for every Learner. `challenge` is null when none is written for today.

    Its Questions come without their answers until the Learner has answered them; each answered
    one carries its first try's outcome, the correct answer, Explanation and Sources. Once
    finished it has its Result Card. `streak` is the Learner's Streak on this Stack (#18)."""
    stack = active.stack
    challenge = challenges.todays_challenge(session, stack.id, now)
    state = (
        None if challenge is None else challenges.challenge_state(session, active, challenge, now)
    )
    return schemas.TodaysChallengeOut(
        stack_id=stack.id,
        stack_name=stack.name,
        day=review.utc_day(now),
        streak=challenges.streak(session, active.learner_id, stack.id, now),
        challenge=None if state is None else _challenge_out(stack.name, state),
    )


@router.get("/stacks/{stack_id}/challenges")
def get_archive(active: ActiveStackInPath, session: SessionDep, now: Now) -> schemas.ArchiveOut:
    """This Active Stack's Archive (#19): every released Daily Challenge, back to #1, newest
    first, each with the Learner's status and first score. An Upcoming Challenge is never in it.
    Any of them can be played (`GET /stacks/{stack_id}/challenges/{number}`)."""
    stack = active.stack
    return schemas.ArchiveOut(
        stack_id=stack.id,
        stack_name=stack.name,
        day=review.utc_day(now),
        challenges=[_archived(stack.name, a) for a in challenges.archive(session, active, now)],
    )


@router.get("/stacks/{stack_id}/challenges/{number}")
def get_archived_challenge(
    number: int, active: ActiveStackInPath, session: SessionDep, now: Now
) -> schemas.StackChallengeOut:
    """Daily Challenge #`number` from this Active Stack's Archive, as the Learner has played it,
    exactly as today's is sent (`GET /stacks/{stack_id}/challenges/today`). 404 for one that
    doesn't exist or isn't released yet."""
    stack = active.stack
    challenge = challenges.released_challenge(session, stack.id, number, now)
    if challenge is None:
        raise HTTPException(404, "Daily Challenge not found")
    state = challenges.challenge_state(session, active, challenge, now)
    return schemas.StackChallengeOut(
        stack_id=stack.id,
        stack_name=stack.name,
        day=review.utc_day(now),
        challenge=_challenge_out(stack.name, state),
    )


@router.get("/catch-up")
def get_catch_up(learner: CurrentLearner, session: SessionDep, now: Now) -> schemas.CatchUpOut:
    """Catch-up (#19): for each of the Learner's Active Stacks, the past Daily Challenges in its
    Archive they haven't finished (not today's, which is home's), newest first, with a count.
    Optional: it never blocks anything."""
    return schemas.CatchUpOut(
        stacks=[
            schemas.CatchUpStackOut(
                stack_id=s.record.stack.id,
                stack_name=s.record.stack.name,
                count=len(s.challenges),
                challenges=[_archived(s.record.stack.name, a) for a in s.challenges],
            )
            for s in challenges.catch_up(session, onboarding.active_stacks(session, learner), now)
        ]
    )


@router.post("/stacks/{stack_id}/challenges/{number}/answers")
def answer_challenge_question(
    number: int,
    body: schemas.ChallengeAnswerIn,
    active: ActiveStackInPath,
    session: SessionDep,
    grader: GraderDep,
    now: Now,
) -> schemas.ChallengeAnswerOut:
    """Answer one Question of Daily Challenge #`number`, today's or any other released one in
    the Archive (#19): a choice ID, a written answer, or null. Scoring is the server's. A past
    Challenge's play is scored the same, with its misses recorded, but never counts toward a
    Streak. Only the first answer to each Question counts (`counted`); a wrong
    one is a Missed Question. Any later answer, such as a replay after finishing, is marked and
    shown but changes no score, Streak or Missed Question. The result carries the correct
    answer or Model Answer, the grader's feedback (written), the Explanation and every Source,
    and the Challenge after it.

    A written first answer that can't be graded is recorded as ungraded (`outcome`): it earns no
    point, and the Learner can resubmit for feedback only.

    404 for a Challenge that doesn't exist or isn't released yet; 409 `question_retired`; 422
    `question_not_in_challenge`, `not_a_choice` or `answer_too_long`; 503 `grading_failed` when
    an answer that doesn't count can't be graded. In each of those nothing is recorded.
    """
    try:
        result = challenges.answer(
            session, active, number, body.question_id, body.answer, grader, now
        )
    except challenges.ChallengeNotFound as error:
        raise HTTPException(404, "Daily Challenge not found") from error
    except challenges.QuestionRetired as error:
        raise HTTPException(409, QUESTION_RETIRED) from error
    except challenges.QuestionNotInChallenge as error:
        detail = {
            "code": "question_not_in_challenge",
            "message": f"Not a Question of this Daily Challenge: {error.question_id}",
        }
        raise HTTPException(422, detail) from error
    except marking.NotAChoice as error:
        raise _not_a_choice(error) from error
    except marking.AnswerTooLong as error:
        raise _answer_too_long(error) from error
    except grading.GradingFailed as error:
        raise HTTPException(503, CHALLENGE_GRADING_FAILED) from error
    return schemas.ChallengeAnswerOut(
        counted=result.counted,
        outcome=result.outcome,
        question=_answered_question(result.question, result.response, result.feedback),
        challenge=_challenge_out(active.stack.name, result.state),
    )


# --- Review ----------------------------------------------------------------------------------

NOT_IN_REVIEW = {
    "code": "not_in_review",
    "message": "This Question isn't in your Review right now.",
}


@router.get("/review")
def get_review_set(learner: CurrentLearner, session: SessionDep, now: Now) -> schemas.ReviewSetOut:
    """A Review set across all the Learner's Active Stacks: up to ten Questions, without their
    answers, to answer one at a time. Missed Questions come first (oldest first), then Updated
    Lessons' new Questions, then spaced repeats from Completed Lessons (app/review.py). Empty
    when nothing is due.

    Review is optional and never blocks anything. Sets aren't stored: every request draws the
    set afresh, so once its Questions are answered the next request draws the next set. 409
    `onboarding_needed` before onboarding."""
    records = onboarding.active_stacks(session, learner)
    if not records:
        raise HTTPException(409, ONBOARDING_NEEDED)
    return schemas.ReviewSetOut(
        size=review.SET_SIZE,
        max_answer_chars=grading.MAX_ANSWER_CHARS,
        questions=[
            schemas.ReviewQuestionOut(
                **_quiz_question(r.question).model_dump(),
                stack_id=r.stack.id,
                stack_name=r.stack.name,
            )
            for r in reviews.review_set(session, records, now)
        ],
    )


@router.post("/review/answers")
def answer_review_question(
    body: schemas.ReviewAnswerIn,
    learner: CurrentLearner,
    session: SessionDep,
    grader: GraderDep,
    now: Now,
) -> schemas.ReviewAnswerOut:
    """Answer one Question of the Learner's Review on its Active Stack: a choice ID, a written
    answer, or null. The result carries the Question's correct answer or Model Answer, the
    grader's feedback (written) and its Explanation, for the page to show after a miss.

    409 `not_in_review` for a Question that isn't in the Learner's Review queue now (a Locked
    Lesson's, or one already answered correctly today); 409 `not_active_stack` or 404 for the
    Stack; 422 `not_a_choice` or `answer_too_long`; 503 `grading_failed` when a written answer
    can't be graded. In each of those nothing is recorded.
    """
    record = get_active_stack_in_path(body.stack_id, learner, session)
    try:
        result = reviews.answer_question(
            session, record, body.question_id, body.answer, grader, now
        )
    except reviews.NotInReview as error:
        raise HTTPException(409, NOT_IN_REVIEW) from error
    except marking.NotAChoice as error:
        raise _not_a_choice(error) from error
    except marking.AnswerTooLong as error:
        raise _answer_too_long(error) from error
    except grading.GradingFailed as error:
        raise HTTPException(503, GRADING_FAILED) from error
    return schemas.ReviewAnswerOut(
        correct=result.correct,
        question=_answered_question(result.question, result.response, result.feedback),
    )


@router.put("/stacks/{stack_id}/milestones/{milestone_id}")
def tick_milestone(
    milestone_id: str,
    body: schemas.MilestoneTickIn,
    active: ActiveStackInPath,
    session: SessionDep,
    now: Now,
) -> schemas.MilestoneTickOut:
    """Tick or untick a Milestone of this Active Stack. Ticks never change any lock state."""
    if lessons.find_current_milestone(session, active.stack_id, milestone_id) is None:
        raise HTTPException(404, "Milestone not found")
    progress.set_milestone_ticked(session, active, milestone_id, body.ticked, now)
    return schemas.MilestoneTickOut(id=milestone_id, ticked=body.ticked)


# --- Settings: grading key, access tokens, drafts ---------------------------------------------


def _grading(
    session: Session, learner: Learner, box: llm_keys.KeyBox, admin_emails: frozenset[str]
) -> schemas.GradingOut:
    own = llm_keys.summary(session, learner)
    grader = (
        "own_key"
        if own is not None and box.enabled
        else "admin_key"
        if box.enabled and llm_keys.admin_has_key(session, admin_emails)
        else "server"
    )
    return schemas.GradingOut(
        key=schemas.GradingKeyOut.model_validate(own) if own else None,
        grader=grader,
        keys_enabled=box.enabled,
        default_model=grading.NVIDIA_MODEL,
    )


@router.get("/me/grading")
def get_grading(
    learner: CurrentLearner, session: SessionDep, verifier: VerifierDep, box: KeyBoxDep
) -> schemas.GradingOut:
    """How the Learner's written answers are graded, and their saved key (never the key)."""
    return _grading(session, learner, box, verifier.settings.admin_emails)


@router.put("/me/grading-key")
def save_grading_key(
    body: schemas.GradingKeyIn,
    learner: CurrentLearner,
    session: SessionDep,
    verifier: VerifierDep,
    box: KeyBoxDep,
    now: Now,
) -> schemas.GradingOut:
    """Save (or replace) the Learner's LLM key for grading, encrypted. 503 when the server has
    no LLM_KEY_SECRET; 422 for a key or model that can't be right."""
    try:
        llm_keys.save_key(
            session, box, learner, body.api_key, now, provider=body.provider, model=body.model
        )
    except llm_keys.KeysDisabled as error:
        raise HTTPException(
            503, "This server can't store keys yet: the Admin must set LLM_KEY_SECRET."
        ) from error
    except llm_keys.BadKey as error:
        raise HTTPException(422, str(error)) from error
    return _grading(session, learner, box, verifier.settings.admin_emails)


@router.delete("/me/grading-key")
def remove_grading_key(
    learner: CurrentLearner, session: SessionDep, verifier: VerifierDep, box: KeyBoxDep
) -> schemas.GradingOut:
    llm_keys.remove_key(session, learner)
    return _grading(session, learner, box, verifier.settings.admin_emails)


@router.get("/me/access-tokens")
def list_access_tokens(
    learner: CurrentLearner, session: SessionDep
) -> list[schemas.AccessTokenOut]:
    return [
        schemas.AccessTokenOut.model_validate(t)
        for t in access_tokens.list_tokens(session, learner)
    ]


@router.post("/me/access-tokens", status_code=201)
def create_access_token(
    body: schemas.AccessTokenIn, learner: CurrentLearner, session: SessionDep, now: Now
) -> schemas.NewAccessTokenOut:
    """A new personal access token for the MCP connector. The token is in this response only."""
    try:
        new = access_tokens.create(session, learner, body.name, now)
    except access_tokens.TooManyTokens as error:
        raise HTTPException(
            422, f"You have {access_tokens.MAX_TOKENS} tokens: revoke one first."
        ) from error
    return schemas.NewAccessTokenOut(
        **schemas.AccessTokenOut.model_validate(new.row).model_dump(), token=new.token
    )


@router.delete("/me/access-tokens/{token_id}", status_code=204)
def revoke_access_token(
    token_id: int, learner: CurrentLearner, session: SessionDep, now: Now
) -> Response:
    try:
        access_tokens.revoke(session, learner, token_id, now)
    except access_tokens.TokenNotFound as error:
        raise HTTPException(404, "Token not found") from error
    return Response(status_code=204)


def _draft_out(draft: ContentDraft, author: str) -> schemas.DraftOut:
    return schemas.DraftOut(
        id=draft.id,
        stack_id=draft.stack_id,
        kind=draft.kind,
        status=draft.status,
        author_email=author,
        note=draft.note,
        payload=draft.payload,
        created_at=draft.created_at,
        decided_at=draft.decided_at,
    )


@router.get("/admin/drafts")
def list_drafts(_: AdminLearner, session: SessionDep) -> list[schemas.DraftOut]:
    """Drafts submitted through the MCP connector, pending first, then newest first."""
    rows = session.execute(
        select(ContentDraft, Learner.email)
        .join(Learner, Learner.id == ContentDraft.learner_id)
        .order_by((ContentDraft.status != "pending"), ContentDraft.created_at.desc())
        .limit(200)
    ).all()
    return [_draft_out(d, email) for d, email in rows]


@router.put("/admin/drafts/{draft_id}")
def decide_draft(
    draft_id: int,
    body: schemas.DraftDecisionIn,
    _: AdminLearner,
    session: SessionDep,
    now: Now,
) -> schemas.DraftOut:
    """Accept or reject a pending draft. An accepted one waits for `content-export-drafts`."""
    draft = session.get(ContentDraft, draft_id)
    if draft is None:
        raise HTTPException(404, "Draft not found")
    if draft.status not in ("pending", "accepted", "rejected"):
        raise HTTPException(409, "This draft was exported already.")
    draft.status, draft.decided_at = body.status, now
    session.commit()
    author = session.get(Learner, draft.learner_id)
    return _draft_out(draft, author.email if author else "")


@router.get("/stack-requests")
def list_stack_requests(_: CurrentLearner, session: SessionDep) -> list[schemas.StackPlanOut]:
    """Stacks requested but not live yet, newest first, with how far each is built."""
    return [
        schemas.StackPlanOut.model_validate(p.summary())
        for p in stack_builder.requested_stacks(session)
    ]


@router.post("/stack-requests", status_code=201)
def request_stack(
    body: schemas.StackRequestIn, learner: CurrentLearner, session: SessionDep, now: Now
) -> schemas.StackPlanOut:
    """Ask for a new Stack. Claude then builds it through the MCP connector: the weekly plan
    first, then the quiz setup."""
    try:
        draft = stack_builder.request_stack(
            session,
            learner,
            stack_id=body.id,
            name=body.name,
            summary=body.summary,
            audience=body.audience,
            weeks=body.weeks,
            notes=body.notes,
            now=now,
        )
    except stack_builder.RequestRefused as error:
        raise HTTPException(422, str(error)) from error
    found = stack_builder.plan(session, draft.stack_id)
    assert found is not None
    return schemas.StackPlanOut.model_validate(found.summary())


@router.delete("/stack-requests/{stack_id}", status_code=204)
def delete_stack_request(
    stack_id: str, learner: CurrentLearner, session: SessionDep, verifier: VerifierDep
) -> Response:
    """Delete a Stack being built, with all its drafts. Its requester or the Admin only."""
    try:
        stack_builder.delete_request(
            session,
            learner,
            stack_id,
            is_admin=learners.is_admin(learner, verifier.settings.admin_emails),
        )
    except stack_builder.RequestNotFound as error:
        raise HTTPException(404, "Stack request not found") from error
    except stack_builder.RequestRefused as error:
        raise HTTPException(409, str(error)) from error
    return Response(status_code=204)


def create_app(
    verifier: TokenVerifier | None = None,
    grader: grading.Grader | None = None,
    *,
    key_box: llm_keys.KeyBox | None = None,
    mcp_session_scope: mcp_server.SessionScope | None = None,
    mcp_now: Callable[[], datetime] | None = None,
) -> FastAPI:
    """The API. Session tokens are checked by `verifier`, by default the one CLERK_* configures;
    written answers are graded by `grader`, by default the Claude Code CLI (CLAUDE_BIN), unless
    the Learner or the Admin saved an LLM key (encrypted by `key_box`, from LLM_KEY_SECRET).

    The MCP connector is mounted at /mcp/, signed in by personal access tokens; its database
    sessions come from `mcp_session_scope` and its clock from `mcp_now` (tests pass their own)."""
    _configure_logging()
    app_verifier = verifier or TokenVerifier.from_config()
    admin_emails = app_verifier.settings.admin_emails if app_verifier else frozenset[str]()
    server = mcp_server.build_server(
        mcp_session_scope or _session_scope, mcp_now or get_now, admin_emails
    )
    mcp_app = server.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        json_response=True,
        # The Host check guards against DNS rebinding, where a web page makes the browser send
        # the user's cookies to a local server. The connector takes no cookies: every request
        # needs a bearer token, which a browser never adds by itself. So any host may serve it.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async with server.session_manager.run():
            yield

    app = FastAPI(title="Learning App API", lifespan=lifespan)
    app.state.verifier = app_verifier
    app.state.grader = grader or grading.grader_from_config(config.CLAUDE_BIN)
    app.state.key_box = key_box or llm_keys.KeyBox(config.LLM_KEY_SECRETS)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    app.mount(
        "/mcp",
        mcp_server.BearerTokenAuth(
            mcp_app, mcp_session_scope or _session_scope, mcp_now or get_now, admin_emails
        ),
    )
    return app


@contextmanager
def _session_scope() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


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
