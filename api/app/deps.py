"""FastAPI dependencies shared by the routes.

- `SessionDep`: a database session.
- `CurrentLearner`: the signed-in Learner. Every route on the main router already requires it,
  so a route that needs the Learner just declares `learner: CurrentLearner`; FastAPI runs the
  check once per request.
- `AdminLearner`: the same, but refused with 403 unless the Learner is the Admin.
- `ActiveStack`: the signed-in Learner's record on their Active Stack (`LearnerStack`, with its
  `stack` loaded). Refused with 409 `onboarding_needed` until the Learner has onboarded, so any
  route about studying declares `active: ActiveStack` and gets `active.learner_id` /
  `active.stack_id` for the progress it reads or writes.
- `ActiveStackInPath`: the same, for a route under `/stacks/{stack_id}` that changes progress;
  refused with 409 `not_active_stack` unless the path names the Active Stack.
- `UnlockedLesson`: the guard on starting a Lesson Quiz. Only the Learner's Unlocked Lesson
  gets through, whatever the browser shows, and not while a Pending Review Round exists.
- `Now`: the current time (timezone-aware UTC). Every route reads the clock through it, never
  `datetime.now`, so tests override `get_now` with a clock they control.
- `open_daily_review`: the Daily Review's "first use of the day" hook. The main router runs it
  on every request, after signing in and before the route; see `reviews.start_day`.
- `QuizRandom`: the random source that draws a quiz's, a Retake's and a Review Round's
  Questions. Tests override `get_quiz_rng` with a seeded one.
- `GraderDep`: the `Grader` that grades written answers (app/grading.py), set on the app by
  `create_app`. Pass it to `marking.mark` / `mark_all`. Tests override `get_grader` with a fake.
"""

import random
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import learners, lessons, onboarding, progress, reviews
from app.auth import Identity, InvalidToken, KeysUnavailable, TokenVerifier
from app.db import get_session
from app.grading import Grader
from app.models import Learner, LearnerStack, Lesson

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
    "message": "Pick your Active Stack and time zone first.",
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
) -> Learner:
    try:
        return learners.sign_in(session, identity, verifier.settings.admin_emails)
    except learners.NotInvited as error:
        raise HTTPException(403, NOT_INVITED) from error


CurrentLearner = Annotated[Learner, Depends(get_current_learner)]


def get_admin(learner: CurrentLearner, verifier: VerifierDep) -> Learner:
    if not learners.is_admin(learner, verifier.settings.admin_emails):
        raise HTTPException(403, "Only the Admin can do this.")
    return learner


AdminLearner = Annotated[Learner, Depends(get_admin)]


def open_daily_review(
    learner: CurrentLearner, session: SessionDep, now: Now, rng: QuizRandom
) -> None:
    """ "Using the app", for the Daily Review: any signed-in request by an onboarded Learner.
    The first one of the Learner's day opens Round 1 on their Active Stack, if one is owed
    (`reviews.start_day`). The main router runs this on every route, before the route, so the
    route already sees the round."""
    record = onboarding.active_stack(session, learner)
    if record is None or learner.time_zone is None:
        return
    reviews.start_day(session, record, learner.time_zone, now, rng)


def get_active_stack(learner: CurrentLearner, session: SessionDep) -> LearnerStack:
    record = onboarding.active_stack(session, learner)
    if record is None or onboarding.needs_onboarding(learner):
        raise HTTPException(409, ONBOARDING_NEEDED)
    return record


ActiveStack = Annotated[LearnerStack, Depends(get_active_stack)]

NOT_ACTIVE_STACK = {
    "code": "not_active_stack",
    "message": "This isn't your Active Stack. Switch to it in Settings first.",
}


def get_active_stack_in_path(stack_id: str, active: ActiveStack) -> LearnerStack:
    if stack_id != active.stack_id:
        raise HTTPException(409, NOT_ACTIVE_STACK)
    return active


ActiveStackInPath = Annotated[LearnerStack, Depends(get_active_stack_in_path)]
"""For a route under `/stacks/{stack_id}` that changes progress: the Learner's record on their
Active Stack, refused with 409 `not_active_stack` unless `stack_id` is that Stack."""

LESSON_LOCKED = {
    "code": "lesson_locked",
    "message": "This Lesson is locked. Complete the Lessons before it first.",
}

LESSON_COMPLETED = {
    "code": "lesson_completed",
    "message": "You've already completed this Lesson.",
}


REVIEW_ROUND_PENDING = {
    "code": "review_round_pending",
    "message": "Finish your Review Round to unlock this Lesson.",
}


def get_unlocked_lesson(
    lesson_id: str,
    active: ActiveStackInPath,
    learner: CurrentLearner,
    session: SessionDep,
    now: Now,
) -> Lesson:
    lesson = lessons.find_current_lesson(session, active.stack_id, lesson_id)
    if lesson is None:
        raise HTTPException(404, "Lesson not found")
    learner_id, stack_id, time_zone = active.learner_id, active.stack_id, learner.time_zone
    state = progress.lesson_states(session, learner_id, stack_id, time_zone, now)[lesson.id]
    if state == "completed":
        raise HTTPException(409, LESSON_COMPLETED)
    if state == "locked":
        pending = progress.pending_review_round(session, learner_id, stack_id, time_zone, now)
        waiting = progress.waiting_for_review(session, learner_id, stack_id, time_zone, now)
        if pending is not None and waiting == lesson.id:
            raise HTTPException(409, {**REVIEW_ROUND_PENDING, "round_id": str(pending.id)})
        raise HTTPException(409, LESSON_LOCKED)
    return lesson


UnlockedLesson = Annotated[Lesson, Depends(get_unlocked_lesson)]
"""For a route under `/stacks/{stack_id}/lessons/{lesson_id}` that starts a Lesson Quiz: the
Learner's Unlocked Lesson (current Syllabus version, Week and Materials loaded). Anything else is
refused, whatever the browser shows: 409 `review_round_pending` (with the pending `round_id`)
for the Unlocked Lesson while a Pending Review Round exists (#9), 409 `lesson_locked` for any
other Locked Lesson, 409 `lesson_completed` for a Completed Lesson, 409 `not_active_stack`, or
404."""


def get_grader(request: Request) -> Grader:
    grader: Grader = request.app.state.grader
    return grader


GraderDep = Annotated[Grader, Depends(get_grader)]
