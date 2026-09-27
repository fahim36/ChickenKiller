"""FastAPI dependencies shared by the routes.

- `SessionDep`: a database session.
- `CurrentLearner`: the signed-in Learner. Every route on the main router already requires it,
  so a route that needs the Learner just declares `learner: CurrentLearner`; FastAPI runs the
  check once per request.
- `AdminLearner`: the same, but refused with 403 unless the Learner is the Admin.
- `ActiveStackInPath`: for a route about studying, all under `/stacks/{stack_id}`: the
  signed-in Learner's record on the Stack in the path (`LearnerStack`, with its `stack`
  loaded), which must be one of their Active Stacks. Refused with 409 `onboarding_needed` until
  the Learner has onboarded, 404 for an unknown Stack, and 409 `not_active_stack` for any other
  Stack. The route gets `active.learner_id` / `active.stack_id` for the progress it reads or
  writes.
- `UnlockedLesson`: the guard on starting a Lesson Quiz. Only the Learner's Unlocked Lesson
  gets through, whatever the browser shows.
- `Now`: the current time (timezone-aware UTC). Every route reads the clock through it, never
  `datetime.now`, so tests override `get_now` with a clock they control.
- `QuizRandom`: the random source that draws a quiz's and a Retake's Questions. Tests override
  `get_quiz_rng` with a seeded one.
- `GraderDep`: the `Grader` that grades written answers (app/grading.py), set on the app by
  `create_app`. Pass it to `marking.mark` / `mark_all`. Tests override `get_grader` with a fake.
"""

import random
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import learners, lessons, onboarding, progress
from app.auth import Identity, InvalidToken, KeysUnavailable, TokenVerifier
from app.db import get_session
from app.grading import Grader
from app.models import Learner, LearnerStack, Lesson, Stack

SessionDep = Annotated[Session, Depends(get_session)]


def get_now() -> datetime:
    return datetime.now(UTC)


Now = Annotated[datetime, Depends(get_now)]


def get_quiz_rng() -> random.Random:
    return random.Random()


QuizRandom = Annotated[random.Random, Depends(get_quiz_rng)]

NOT_INVITED = {
    "code": "not_invited",
    "message": "This email address hasn't been invited. Ask the Admin for an invitation.",
}

ONBOARDING_NEEDED = {
    "code": "onboarding_needed",
    "message": "Pick the Stacks you want to study first.",
}

_bearer = HTTPBearer(auto_error=False)


def get_verifier(request: Request) -> TokenVerifier:
    verifier: TokenVerifier | None = request.app.state.verifier
    if verifier is None:
        raise HTTPException(503, "Sign-in isn't configured on this server: set CLERK_ISSUER.")
    return verifier


VerifierDep = Annotated[TokenVerifier, Depends(get_verifier)]


def get_identity(
    verifier: VerifierDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Identity:
    challenge = {"WWW-Authenticate": "Bearer"}
    if credentials is None:
        raise HTTPException(401, "Sign in first.", headers=challenge)
    try:
        return verifier.verify(credentials.credentials)
    except KeysUnavailable as error:
        raise HTTPException(503, "Sign-in can't be checked right now. Try again soon.") from error
    except InvalidToken as error:
        detail = "Your sign-in is invalid or has expired."
        raise HTTPException(401, detail, headers=challenge) from error


def get_current_learner(
    session: SessionDep,
    verifier: VerifierDep,
    identity: Annotated[Identity, Depends(get_identity)],
    now: Now,
) -> Learner:
    try:
        return learners.sign_in(session, identity, verifier.settings.admin_emails, now)
    except learners.NotInvited as error:
        raise HTTPException(403, NOT_INVITED) from error


CurrentLearner = Annotated[Learner, Depends(get_current_learner)]


def get_admin(learner: CurrentLearner, verifier: VerifierDep) -> Learner:
    if not learners.is_admin(learner, verifier.settings.admin_emails):
        raise HTTPException(403, "Only the Admin can do this.")
    return learner


AdminLearner = Annotated[Learner, Depends(get_admin)]


NOT_ACTIVE_STACK = {
    "code": "not_active_stack",
    "message": "This isn't one of your Active Stacks. Activate it in Settings first.",
}


def get_active_stack_in_path(
    stack_id: str, learner: CurrentLearner, session: SessionDep
) -> LearnerStack:
    record = onboarding.active_stack(session, learner, stack_id)
    if record is not None:
        return record
    if onboarding.needs_onboarding(session, learner):
        raise HTTPException(409, ONBOARDING_NEEDED)
    if session.get(Stack, stack_id) is None:
        raise HTTPException(404, "Stack not found")
    raise HTTPException(409, NOT_ACTIVE_STACK)


ActiveStackInPath = Annotated[LearnerStack, Depends(get_active_stack_in_path)]
"""For a route under `/stacks/{stack_id}`: the Learner's record on that Stack, which must be one
of their Active Stacks. 409 `onboarding_needed` before onboarding, 404 for a Stack that doesn't
exist, and 409 `not_active_stack` for one that isn't Active."""

LESSON_LOCKED = {
    "code": "lesson_locked",
    "message": "This Lesson is locked. Complete the Lessons before it first.",
}

LESSON_COMPLETED = {
    "code": "lesson_completed",
    "message": "You've already completed this Lesson.",
}

LESSON_UPDATED = {
    "code": "lesson_updated",
    "message": (
        "This Lesson was added or changed after you'd passed it. "
        "Its new Questions come in your Review."
    ),
}


def get_unlocked_lesson(lesson_id: str, active: ActiveStackInPath, session: SessionDep) -> Lesson:
    lesson = lessons.find_current_lesson(session, active.stack_id, lesson_id)
    if lesson is None:
        raise HTTPException(404, "Lesson not found")
    state = progress.lesson_states(session, active.learner_id, active.stack_id)[lesson.id]
    if state == "completed":
        raise HTTPException(409, LESSON_COMPLETED)
    if state == "updated":
        raise HTTPException(409, LESSON_UPDATED)
    if state == "locked":
        raise HTTPException(409, LESSON_LOCKED)
    return lesson


UnlockedLesson = Annotated[Lesson, Depends(get_unlocked_lesson)]
"""For a route under `/stacks/{stack_id}/lessons/{lesson_id}` that starts a Lesson Quiz: the
Learner's Unlocked Lesson (current Syllabus version, Week and Materials loaded). Anything else is
refused, whatever the browser shows: 409 `lesson_locked` for a Locked Lesson, 409
`lesson_completed` for a Completed Lesson, 409 `lesson_updated` for an Updated Lesson (#13: its
new Questions come in Review), 409 `not_active_stack`, or 404."""


def get_grader(request: Request) -> Grader:
    grader: Grader = request.app.state.grader
    return grader


GraderDep = Annotated[Grader, Depends(get_grader)]
