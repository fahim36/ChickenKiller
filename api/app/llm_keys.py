"""Learners' own LLM provider keys for grading written answers.

A Learner may save a key for NVIDIA's API (Nemotron) in Settings. Their written answers are
then graded with it (`grading.ChatCompletionsGrader`). A Learner without a key is graded with
the Admin's key, when the Admin has saved one, and otherwise by the default grader, the Claude
Code CLI on the API's machine (ADR-0006). So `grader_for` picks, in order: the Learner's own
key, the Admin's key, the default.

Keys are secrets. They are stored only encrypted (Fernet: AES-128-CBC with an HMAC), with the
server's `LLM_KEY_SECRET`, which never goes in the database. The API never sends a key back:
only its provider, model and last four characters (`key_hint`). Without `LLM_KEY_SECRET` no key
can be saved (`KeysDisabled`), and saved ones can't be read, so grading falls back to the
default. A key that can't be decrypted (the secret changed) is skipped the same way, and logged.
"""

import logging
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.grading import (
    NVIDIA_BASE_URL,
    NVIDIA_MODEL,
    ChatCompletionsGrader,
    FallbackGrader,
    Grader,
    NoKeyGrader,
)
from app.models import GradingKey, Learner

logger = logging.getLogger(__name__)

PROVIDERS = {"nvidia": (NVIDIA_BASE_URL, NVIDIA_MODEL)}
"""Each provider's endpoint and default model."""

MIN_KEY_CHARS = 20
MAX_KEY_CHARS = 400


class KeysDisabled(Exception):
    """The server has no LLM_KEY_SECRET, so keys can't be stored."""


class BadKey(Exception):
    """The key or model given can't be right (empty, too short or long, or an odd model)."""


@dataclass(frozen=True)
class KeySummary:
    """What the Learner sees of a saved key: never the key itself."""

    provider: str
    model: str
    key_hint: str
    updated_at: datetime


class KeyBox:
    """Encrypts and decrypts keys with the server's secrets (the first encrypts; any of them
    decrypts, so a secret can be rotated). With no secrets, it is disabled."""

    def __init__(self, secrets: Sequence[str]) -> None:
        self._fernet = MultiFernet([Fernet(s) for s in secrets]) if secrets else None

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    def encrypt(self, key: str) -> str:
        if self._fernet is None:
            raise KeysDisabled()
        return self._fernet.encrypt(key.encode()).decode()

    def decrypt(self, ciphertext: str) -> str | None:
        """The key, or None when it can't be decrypted with these secrets."""
        if self._fernet is None:
            return None
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            return None


def summary(session: Session, learner: Learner) -> KeySummary | None:
    row = session.get(GradingKey, learner.id)
    if row is None:
        return None
    return KeySummary(row.provider, row.model, row.key_hint, row.updated_at)


def save_key(
    session: Session,
    box: KeyBox,
    learner: Learner,
    api_key: str,
    now: datetime,
    *,
    provider: str = "nvidia",
    model: str | None = None,
) -> KeySummary:
    """Save (or replace) the Learner's key, encrypted. Raises KeysDisabled or BadKey."""
    if not box.enabled:
        raise KeysDisabled()
    api_key = api_key.strip()
    if provider not in PROVIDERS:
        raise BadKey("Choose a supported provider.")
    if not MIN_KEY_CHARS <= len(api_key) <= MAX_KEY_CHARS or any(c.isspace() for c in api_key):
        raise BadKey("That doesn't look like an API key.")
    base_url, default_model = PROVIDERS[provider]
    model = (model or "").strip() or default_model
    if len(model) > 120 or any(c.isspace() for c in model):
        raise BadKey("That isn't a model name.")
    row = session.get(GradingKey, learner.id)
    if row is None:
        row = GradingKey(learner_id=learner.id)
        session.add(row)
    row.provider, row.base_url, row.model = provider, base_url, model
    row.key_ciphertext = box.encrypt(api_key)
    row.key_hint = api_key[-4:]
    row.updated_at = now
    session.commit()
    return KeySummary(row.provider, row.model, row.key_hint, row.updated_at)


def remove_key(session: Session, learner: Learner) -> None:
    row = session.get(GradingKey, learner.id)
    if row is not None:
        session.delete(row)
        session.commit()


def admin_has_key(session: Session, admin_emails: Collection[str]) -> bool:
    return _admin_key(session, admin_emails) is not None


def own_key_required(learner: Learner, admin_emails: Collection[str]) -> bool:
    """Whether this Learner is graded only with their own key (OWN_GRADING_KEY_REQUIRED). The
    Admin never is."""
    return config.OWN_GRADING_KEY_REQUIRED and learner.email not in admin_emails


def grader_for(
    session: Session,
    box: KeyBox,
    learner: Learner,
    admin_emails: Collection[str],
    default: Grader,
) -> Grader:
    """The grader for the Learner's written answers: their own key, else the Admin's, else
    `default`. When a key's provider fails (down, or slow past its timeout), the next in line
    grades instead (`FallbackGrader`), so a saved key never makes grading less available.

    When the Learner must use their own key (`own_key_required`), only that key grades, and
    without one every grading raises `GradingKeyNeeded`."""
    own = session.get(GradingKey, learner.id)
    only_own = own_key_required(learner, admin_emails)
    graders: list[Grader] = []
    seen: set[int] = set()
    for row in (own,) if only_own else (own, _admin_key(session, admin_emails)):
        if row is None or row.learner_id in seen:
            continue
        seen.add(row.learner_id)
        key = box.decrypt(row.key_ciphertext)
        if key is None:
            logger.warning("grading_key_unreadable %s", row.learner_id)
            continue
        graders.append(ChatCompletionsGrader(key, base_url=row.base_url, model=row.model))
    if only_own:
        return graders[0] if graders else NoKeyGrader()
    if not graders:
        return default
    return FallbackGrader([*graders, default])


def _admin_key(session: Session, admin_emails: Collection[str]) -> GradingKey | None:
    if not admin_emails:
        return None
    return session.scalar(
        select(GradingKey)
        .join(Learner, Learner.id == GradingKey.learner_id)
        .where(Learner.email.in_(list(admin_emails)))
        .order_by(GradingKey.updated_at.desc())
        .limit(1)
    )
