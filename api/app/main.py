from datetime import UTC, datetime

from fastapi import APIRouter, Depends, FastAPI, HTTPException

from app import learners, lessons, onboarding, progress, schemas
from app.auth import TokenVerifier
from app.deps import (
    ActiveStack,
    ActiveStackInPath,
    AdminLearner,
    CurrentLearner,
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


QUIZ_NOT_BUILT = {
    "code": "quiz_not_built",
    "message": "Lesson Quizzes aren't available yet.",
}


@router.post("/stacks/{stack_id}/lessons/{lesson_id}/quiz")
def start_lesson_quiz(lesson: UnlockedLesson) -> None:
    """Start a Lesson Quiz on the Learner's Unlocked Lesson.

    The guard (`UnlockedLesson`) is final: the backend refuses a Locked Lesson's quiz whatever
    the browser shows. The quiz itself is #6, which replaces this body with drawing the
    Questions; until then a Learner the guard lets through gets 501 `quiz_not_built`.
    """
    raise HTTPException(501, QUIZ_NOT_BUILT)


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


def create_app(verifier: TokenVerifier | None = None) -> FastAPI:
    """The API. Session tokens are checked by `verifier`, by default the one CLERK_* configures."""
    app = FastAPI(title="Learning App API")
    app.state.verifier = verifier or TokenVerifier.from_config()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app


app = create_app()
