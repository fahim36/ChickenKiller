import copy
import json
import os
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import jwt
import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.auth import AuthSettings, TokenVerifier
from app.config import normalize_database_url
from app.db import get_session
from app.main import create_app

API_DIR = Path(__file__).resolve().parents[1]
# Tests need a real Postgres (ADR-0002): `docker compose up -d db` locally, a service in CI.
TEST_DATABASE_URL = normalize_database_url(
    os.environ.get(
        "TEST_DATABASE_URL", "postgresql+psycopg://learning:learning@localhost:5433/learning_test"
    )
)

LESSON = "w01-l01"


def _mc(lesson: str, n: int, concept: str) -> dict[str, Any]:
    return {
        "id": f"{lesson}-q{n:02}",
        "concept": concept,
        "type": "multiple_choice",
        "prompt": f"Question {n}?",
        "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
        "answer": "a",
        "explanation": "Because.",
        "materials": ["mat-docs"],
    }


def _written(lesson: str, n: int, concept: str) -> dict[str, Any]:
    return {
        "id": f"{lesson}-q{n:02}",
        "concept": concept,
        "type": "written",
        "prompt": f"Explain {n}.",
        "model_answer": {"summary": "S", "key_points": ["one", "two"]},
        "explanation": "Because.",
        "materials": [],
    }


SYLLABUS: dict[str, Any] = {
    "schema_version": 1,
    "version": "v2026-01-01",
    "stack": {"id": "mini-stack", "name": "Mini Stack", "summary": "A tiny Stack for tests."},
    "materials": [
        {
            "id": "mat-docs",
            "title": "Some docs",
            "url": "https://example.com/docs",
            "type": "docs",
            "subject": "Python",
        },
        {
            "id": "mat-video",
            "title": "A video",
            "url": "https://example.com/video",
            "type": "video",
            "subject": "Python",
        },
    ],
    "weeks": [
        {
            "id": "w01",
            "number": 1,
            "title": "Week one",
            "goal": "Learn things.",
            "deliverable": "A thing.",
            "interview_checks": ["Why?"],
            "lessons": [
                {
                    "id": LESSON,
                    "title": "First lesson",
                    "topics": ["Topic A", "Topic B"],
                    "exercise": "Do it.",
                    "minutes": 60,
                    "materials": ["mat-docs", "mat-video"],
                },
                {
                    "id": "w01-l02",
                    "title": "Second lesson",
                    "topics": ["Topic C"],
                    "exercise": None,
                    "minutes": 60,
                    "materials": [],
                },
            ],
            "milestones": [
                {
                    "id": "w01-m01",
                    "title": "Build it",
                    "kind": "build",
                    "minutes": 120,
                    "materials": ["mat-docs"],
                },
            ],
        }
    ],
}


def make_bank(lesson: str = LESSON, concept_prefix: str = "concept") -> dict[str, Any]:
    """A valid Question Bank for `lesson`: 4 Concepts, 6 multiple-choice and 2 written."""
    c = [f"{concept_prefix}-{x}" for x in "abcd"]
    return {
        "schema_version": 1,
        "lesson_id": lesson,
        "concepts": [{"id": cid, "name": f"Concept {cid}"} for cid in c],
        "questions": [
            _mc(lesson, 1, c[0]),
            _mc(lesson, 2, c[0]),
            _mc(lesson, 3, c[1]),
            _mc(lesson, 4, c[1]),
            _mc(lesson, 5, c[2]),
            _mc(lesson, 6, c[2]),
            _written(lesson, 7, c[3]),
            _written(lesson, 8, c[3]),
        ],
    }


BANK = make_bank()


def changelog_entry(kind: str, item_id: str, change: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "id": item_id,
        "change": change,
        "what": f"{change} {item_id}",
        "why": "The field moved on.",
        "sources": ["https://example.com/release-notes"],
    }


def make_changelog(version: str, previous: str | None, *entries: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "version": version,
        "previous_version": previous,
        "summary": "What changed in this version.",
        "changes": list(entries),
    }


def write_folder(
    root: Path,
    syllabus: dict[str, Any],
    banks: dict[str, dict[str, Any]],
    changelog: dict[str, Any] | None = None,
) -> Path:
    folder = root / "mini-stack" / syllabus["version"]
    (folder / "questions").mkdir(parents=True, exist_ok=True)
    (folder / "syllabus.json").write_text(json.dumps(syllabus), encoding="utf-8")
    for name, bank in banks.items():
        (folder / "questions" / f"{name}.json").write_text(json.dumps(bank), encoding="utf-8")
    if changelog is not None:
        (folder / "changelog.json").write_text(json.dumps(changelog), encoding="utf-8")
    return folder


ContentFactory = Callable[..., Path]
Edit = Callable[[dict[str, Any], dict[str, Any]], None]


def as_version(version: str, edit: Edit | None = None) -> Edit:
    """A `make_content` edit that names the folder's version, then applies `edit`."""

    def apply(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["version"] = version
        if edit:
            edit(syllabus, bank)

    return apply


@pytest.fixture
def make_content(tmp_path: Path) -> ContentFactory:
    """Write a valid folder; pass `edit(syllabus, bank)` to break it for a test,
    `extra_banks` ({file stem: bank}) to add more Question Banks (see `make_bank`), and
    `changelog` (see `make_changelog`) for a version that follows another."""

    def factory(
        edit: Callable[[dict, dict], None] | None = None,
        *,
        extra_banks: dict[str, dict[str, Any]] | None = None,
        changelog: dict[str, Any] | None = None,
    ) -> Path:
        syllabus, bank = copy.deepcopy(SYLLABUS), copy.deepcopy(BANK)
        if edit:
            edit(syllabus, bank)
        banks = {bank.get("lesson_id", LESSON): bank, **(extra_banks or {})}
        return write_folder(tmp_path, syllabus, banks, changelog)

    return factory


def alembic_config(url: str = TEST_DATABASE_URL) -> Config:
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    config.attributes["configure_logger"] = False
    return config


def _create_database_if_missing(url: str) -> None:
    target = make_url(url)
    server = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with server.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": target.database}
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    server.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """The test database, rebuilt from the migrations (down to nothing, then up) once per run."""
    _create_database_if_missing(TEST_DATABASE_URL)
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A session whose work is rolled back after each test, even if the code under test commits."""
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        ) as s:
            yield s
        transaction.rollback()


# --- Signing in -------------------------------------------------------------------------------
# Tests sign their own session tokens with a locally generated RSA key, which stands in for
# Clerk's JWKS endpoint. Everything after the key lookup is the real verification code.

ISSUER = "https://clerk.test.example"
WEB_ORIGIN = "http://localhost:3000"
ADMIN_EMAIL = "admin@example.com"
LEARNER_EMAIL = "learner@example.com"
AUTH_SETTINGS = AuthSettings(
    issuer=ISSUER,
    jwks_url=f"{ISSUER}/.well-known/jwks.json",
    authorized_parties=frozenset({WEB_ORIGIN}),
    admin_emails=frozenset({ADMIN_EMAIL}),
)


class LocalKeys:
    """A KeySource holding one public key, in place of Clerk's published JWKS."""

    def __init__(self, private_key: rsa.RSAPrivateKey) -> None:
        self._public_key = private_key.public_key()

    def signing_key(self, token: str) -> Any:
        return self._public_key


@pytest.fixture(scope="session")
def signing_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


TokenFactory = Callable[..., str]


@pytest.fixture
def make_token(signing_key: rsa.RSAPrivateKey) -> TokenFactory:
    """A Clerk-style session token. Override any claim, or pass `key=` to sign with another key."""

    def factory(
        email: str | None = LEARNER_EMAIL,
        sub: str | None = None,
        *,
        key: rsa.RSAPrivateKey | None = None,
        **claims: Any,
    ) -> str:
        now = int(time.time())
        payload: dict[str, Any] = {
            "iss": ISSUER,
            "sub": sub or f"user_{email}",
            "azp": WEB_ORIGIN,
            "iat": now,
            "nbf": now - 5,
            "exp": now + 60,
            **claims,
        }
        if email is not None:
            payload["email"] = email
        return jwt.encode(payload, key or signing_key, algorithm="RS256", headers={"kid": "k1"})

    return factory


@pytest.fixture
def app(session: Session, signing_key: rsa.RSAPrivateKey) -> FastAPI:
    """The HTTP API, reading and writing through the test session."""
    app = create_app(verifier=TokenVerifier(AUTH_SETTINGS, LocalKeys(signing_key)))
    app.dependency_overrides[get_session] = lambda: session
    return app


@pytest.fixture
def anonymous(app: FastAPI) -> TestClient:
    """A client with no sign-in token."""
    return TestClient(app)


ClientFactory = Callable[..., TestClient]


@pytest.fixture
def signed_in(app: FastAPI, make_token: TokenFactory) -> ClientFactory:
    """`signed_in(email)` is a client whose every request carries that person's session token."""

    def factory(email: str, sub: str | None = None) -> TestClient:
        return TestClient(app, headers={"Authorization": f"Bearer {make_token(email, sub)}"})

    return factory


@pytest.fixture
def admin(signed_in: ClientFactory) -> TestClient:
    return signed_in(ADMIN_EMAIL)


@pytest.fixture
def api(admin: TestClient, signed_in: ClientFactory) -> TestClient:
    """The HTTP API as a Learner the Admin has invited."""
    admin.post("/invitations", json={"email": LEARNER_EMAIL}).raise_for_status()
    return signed_in(LEARNER_EMAIL)
