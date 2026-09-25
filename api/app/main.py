from fastapi import APIRouter, Depends, FastAPI, HTTPException

from app import learners, lessons, schemas
from app.auth import TokenVerifier
from app.deps import AdminLearner, CurrentLearner, SessionDep, VerifierDep, get_current_learner

# Everything except the health check: only a signed-in, invited Learner gets in (app/deps.py).
router = APIRouter(dependencies=[Depends(get_current_learner)])


@router.get("/me")
def me(learner: CurrentLearner, verifier: VerifierDep) -> schemas.MeOut:
    return schemas.MeOut(
        email=learner.email,
        is_admin=learners.is_admin(learner, verifier.settings.admin_emails),
    )


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
def get_syllabus(stack_id: str, session: SessionDep) -> schemas.SyllabusOut:
    syllabus = lessons.current_syllabus(session, stack_id)
    if syllabus is None:
        raise HTTPException(404, "Stack not found")
    stack = syllabus.stack
    return schemas.SyllabusOut(
        id=stack.id,
        name=stack.name,
        summary=stack.summary,
        version=syllabus.version,
        weeks=[schemas.WeekOut.model_validate(week) for week in syllabus.weeks],
    )


@router.get("/stacks/{stack_id}/lessons/{lesson_id}")
def get_lesson(stack_id: str, lesson_id: str, session: SessionDep) -> schemas.LessonOut:
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
        previous_lesson_id=previous_id,
        next_lesson_id=next_id,
    )


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
