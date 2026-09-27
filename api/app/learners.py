"""Who may use the app: the Admin's invitations, and the Learner created on first sign-in."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import Identity
from app.models import Invitation, Learner


class NotInvited(Exception):
    pass


class AlreadyInvited(Exception):
    pass


class AlreadyALearner(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def sign_in(session: Session, identity: Identity, admin_emails: frozenset[str]) -> Learner:
    """The signed-in person's Learner, created on their first sign-in if they were invited.

    The Admin is always let in. Accepting marks the invitation as no longer pending.
    """
    learner = _learner_for(session, identity.clerk_user_id)
    if learner is not None:
        return learner

    invitation = session.scalar(select(Invitation).where(Invitation.email == identity.email))
    if invitation is None and identity.email not in admin_emails:
        raise NotInvited(identity.email)

    learner = Learner(clerk_user_id=identity.clerk_user_id, email=identity.email)
    try:
        with session.begin_nested():
            session.add(learner)
    except IntegrityError:
        # A page's parallel requests can all be someone's first; one of them created it first.
        existing = _learner_for(session, identity.clerk_user_id)
        if existing is None:
            raise
        return existing
    if invitation is not None and invitation.accepted_at is None:
        invitation.accepted_at = datetime.now(UTC)
    session.commit()
    return learner


def is_admin(learner: Learner, admin_emails: frozenset[str]) -> bool:
    return learner.email in admin_emails


def invite(session: Session, email: str) -> Invitation:
    email = normalize_email(email)
    if session.scalar(select(Learner.id).where(Learner.email == email).limit(1)) is not None:
        raise AlreadyALearner(email)
    if session.scalar(select(Invitation.id).where(Invitation.email == email)) is not None:
        raise AlreadyInvited(email)
    invitation = Invitation(email=email)
    session.add(invitation)
    session.commit()
    session.refresh(invitation)
    return invitation


def pending_invitations(session: Session) -> Sequence[Invitation]:
    """Invitations whose person hasn't signed in yet, oldest first."""
    return session.scalars(
        select(Invitation)
        .where(Invitation.accepted_at.is_(None))
        .order_by(Invitation.invited_at, Invitation.id)
    ).all()


def _learner_for(session: Session, clerk_user_id: str) -> Learner | None:
    return session.scalar(select(Learner).where(Learner.clerk_user_id == clerk_user_id))
