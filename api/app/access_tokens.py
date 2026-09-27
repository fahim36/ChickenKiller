"""Personal access tokens for the MCP connector (app/mcp_server.py).

A Learner creates a token in Settings and gives it to their Claude client as the connector's
bearer token. It signs that client in as them, so everything it submits is recorded as theirs
(`ContentDraft.learner_id`). Tokens look like `ica_<43 random characters>`. Only a SHA-256
hash is stored, so a token is shown once, when it is created; after that the Learner sees only
its name and first characters. A token can be revoked at any time and then stops working at
once. Revoking or deleting the Learner's account ends all of them.
"""

import hashlib
import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccessToken, Learner

PREFIX = "ica_"
MAX_TOKENS = 10
"""Live (unrevoked) tokens a Learner may hold at once."""


class TooManyTokens(Exception):
    pass


class TokenNotFound(Exception):
    pass


@dataclass(frozen=True)
class NewToken:
    row: AccessToken
    token: str
    """The token itself: shown once, never stored."""


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create(session: Session, learner: Learner, name: str, now: datetime) -> NewToken:
    live = session.scalars(
        select(AccessToken.id).where(
            AccessToken.learner_id == learner.id, AccessToken.revoked_at.is_(None)
        )
    ).all()
    if len(live) >= MAX_TOKENS:
        raise TooManyTokens()
    token = PREFIX + secrets.token_urlsafe(32)
    row = AccessToken(
        learner_id=learner.id,
        name=name.strip()[:80] or "Claude",
        token_hash=hash_token(token),
        prefix=token[:10],
        created_at=now,
    )
    session.add(row)
    session.commit()
    return NewToken(row, token)


def list_tokens(session: Session, learner: Learner) -> Sequence[AccessToken]:
    """The Learner's live tokens, newest first."""
    return session.scalars(
        select(AccessToken)
        .where(AccessToken.learner_id == learner.id, AccessToken.revoked_at.is_(None))
        .order_by(AccessToken.created_at.desc(), AccessToken.id.desc())
    ).all()


def revoke(session: Session, learner: Learner, token_id: int, now: datetime) -> None:
    row = session.get(AccessToken, token_id)
    if row is None or row.learner_id != learner.id or row.revoked_at is not None:
        raise TokenNotFound(token_id)
    row.revoked_at = now
    session.commit()


def learner_for(session: Session, token: str, now: datetime) -> Learner | None:
    """The Learner a live token signs in, noting when it was used; None for anything else."""
    if not token.startswith(PREFIX):
        return None
    row = session.scalar(
        select(AccessToken).where(
            AccessToken.token_hash == hash_token(token), AccessToken.revoked_at.is_(None)
        )
    )
    if row is None:
        return None
    row.last_used_at = now
    session.commit()
    return session.get(Learner, row.learner_id)
