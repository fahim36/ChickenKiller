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
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import learners, onboarding
from app.auth import Identity, InvalidToken, KeysUnavailable, TokenVerifier
from app.db import get_session
from app.models import Learner, LearnerStack

SessionDep = Annotated[Session, Depends(get_session)]

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


def get_active_stack(learner: CurrentLearner, session: SessionDep) -> LearnerStack:
    record = onboarding.active_stack(session, learner)
    if record is None or onboarding.needs_onboarding(learner):
        raise HTTPException(409, ONBOARDING_NEEDED)
    return record


ActiveStack = Annotated[LearnerStack, Depends(get_active_stack)]
