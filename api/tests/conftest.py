import copy
import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app import progress
from app.auth import AuthSettings, TokenVerifier
from app.config import normalize_database_url
from app.db import get_session
from app.deps import get_grader, get_now
from app.grading import Grade, GradingFailed
from app.main import create_app
from app.models import Learner, LearnerStack, Stack, Syllabus

API_DIR = Path(__file__).resolve().parents[1]
# Tests need a real Postgres (ADR-0002): `docker compose up -d db` locally, a service in CI.
TEST_DATABASE_URL = normalize_database_url(
    os.environ.get(
        "TEST_DATABASE_URL", "postgresql+psycopg://learning:learning@localhost:5433/learning_test"
    )
)

LESSON = "w01-l01"

SOURCES_ACCESSED = "2026-01-01"
"""The day every test Question's Source was accessed. Tests of the rule that a new Question's
Sources are from this run pass `today` to the content check."""


def source(n: int = 1, accessed: str = SOURCES_ACCESSED) -> dict[str, Any]:
    """A Source for a test Question."""
    return {
        "url": f"https://example.com/docs/page-{n}",
        "title": f"Docs page {n}",
        "publisher": "Example",
        "accessed": accessed,
        "claim": "What the Question relies on.",
    }


def mc_question(qid: str, concept: str, lesson: str | None = LESSON) -> dict[str, Any]:
    """A multiple-choice Question whose right answer is "a"."""
    return {
        "id": qid,
        "lesson": lesson,
        "concept": concept,
        "type": "multiple_choice",
        "prompt": f"Question {qid}?",
        "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
        "answer": "a",
        "explanation": "Because.",
        "materials": [],
        "sources": [source()],
    }


def _mc(lesson: str, n: int, concept: str) -> dict[str, Any]:
    return {
        "id": f"{lesson}-q{n:02}",
        "lesson": lesson,
        "concept": concept,
        "type": "multiple_choice",
        "prompt": f"Question {n}?",
        "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
        "answer": "a",
        "explanation": "Because.",
        "materials": ["mat-docs"],
        "sources": [source()],
    }


def _written(lesson: str, n: int, concept: str) -> dict[str, Any]:
    return {
        "id": f"{lesson}-q{n:02}",
        "lesson": lesson,
        "concept": concept,
        "type": "written",
        "prompt": f"Explain {n}.",
        "model_answer": {"summary": "S", "key_points": ["one", "two"]},
        "explanation": "Because.",
        "materials": [],
        "sources": [source()],
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
    """A valid Question Bank file for `lesson`: 4 Concepts, 6 multiple-choice and 2 written
    Questions, all tagged to the Lesson."""
    c = [f"{concept_prefix}-{x}" for x in "abcd"]
    return {
        "schema_version": 2,
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


# --- Daily Challenges (#16) ----------------------------------------------------------------------

LAUNCH = "2026-01-01"
"""The test Stack's launch Day, when its Challenges have one."""

CHALLENGE_MIX = ["w01-l01-q01", "w01-l01-q03", "w01-l01-q07"]
"""Two multiple-choice Questions and one written, from the test bank."""


def challenge(
    number: int, day: str | None = None, questions: list[str] | None = None
) -> dict[str, Any]:
    """Daily Challenge #number, on its Day from LAUNCH unless `day` says otherwise."""
    launch = date.fromisoformat(LAUNCH)
    return {
        "schema_version": 1,
        "number": number,
        "date": day or (launch + timedelta(days=number - 1)).isoformat(),
        "questions": list(questions or CHALLENGE_MIX),
    }


def write_json(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_challenges(stack: Path, *challenges: dict[str, Any], launch: str | None = LAUNCH) -> Path:
    """Replace the Stack's `challenges/` folder: its launch file (unless `launch` is None) and
    one file per Challenge, named by its number. Returns the folder."""
    folder = stack / "challenges"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir()
    if launch is not None:
        write_json(folder / "launch.json", {"schema_version": 1, "launch": launch})
    for c in challenges:
        write_json(folder / f"{c['number']:03}.json", c)
    return folder


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
    """Write a version folder, and replace the Stack's Question Bank with `banks` ({file stem:
    bank file}). Returns the version folder."""
    folder = root / syllabus["stack"]["id"] / syllabus["version"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "syllabus.json").write_text(json.dumps(syllabus), encoding="utf-8")
    bank_dir = folder.parent / "question-bank"
    shutil.rmtree(bank_dir, ignore_errors=True)
    bank_dir.mkdir()
    for name, bank in banks.items():
        (bank_dir / f"{name}.json").write_text(json.dumps(bank), encoding="utf-8")
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
    """Write a valid version folder and the Stack's Question Bank; pass `edit(syllabus, bank)`
    to break them for a test (`bank` is the file for w01-l01), `extra_banks` ({file stem: bank})
    to add more Question Bank files (see `make_bank`), and `changelog` (see `make_changelog`) for
    a version that follows another. Each call replaces the Stack's Question Bank."""

    def factory(
        edit: Callable[[dict, dict], None] | None = None,
        *,
        extra_banks: dict[str, dict[str, Any]] | None = None,
        changelog: dict[str, Any] | None = None,
    ) -> Path:
        syllabus, bank = copy.deepcopy(SYLLABUS), copy.deepcopy(BANK)
        if edit:
            edit(syllabus, bank)
        banks = {LESSON: bank, **(extra_banks or {})}
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


# --- Grading written answers ------------------------------------------------------------------
# Claude is never called in tests: the API grades with this fake (app/grading.py's `Grader`).


class FakeGrader:
    """Passes an answer that contains "right" (any case), with feedback naming the Question's
    first key point otherwise. Set `failing` to make every grading fail, as a timeout would.
    Every call is kept in `calls` as (prompt, model_answer, answer)."""

    def __init__(self) -> None:
        self.failing = False
        self.calls: list[tuple[str, Any, str]] = []

    def grade(self, prompt: str, model_answer: Any, answer: str) -> Grade:
        self.calls.append((prompt, model_answer, answer))
        if self.failing:
            raise GradingFailed("the fake grader is failing")
        if "right" in answer.lower():
            return Grade(passed=True, feedback="Covers every key point.")
        return Grade(passed=False, feedback=f"Missing: {model_answer['key_points'][0]}.")


@pytest.fixture
def grader() -> FakeGrader:
    return FakeGrader()


# --- The clock ---------------------------------------------------------------------------------
# The API reads the time from `deps.get_now`; tests replace it with this clock, so a test can
# say "it is 23:59 UTC" and move time on without waiting.


class FakeClock:
    """A clock that stands still until a test moves it. Starts at the real time."""

    def __init__(self, now: datetime | None = None) -> None:
        self.now = now or datetime.now(UTC)

    def set(self, now: datetime) -> None:
        assert now.tzinfo is not None, "use a timezone-aware time"
        self.now = now

    def advance(self, **delta: float) -> None:
        self.now += timedelta(**delta)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def app(
    session: Session, signing_key: rsa.RSAPrivateKey, grader: FakeGrader, clock: FakeClock
) -> FastAPI:
    """The HTTP API, reading and writing through the test session, grading with `grader` and
    telling the time by `clock`."""
    app = create_app(verifier=TokenVerifier(AUTH_SETTINGS, LocalKeys(signing_key)))
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_grader] = lambda: grader
    app.dependency_overrides[get_now] = lambda: clock.now
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


def onboard(client: TestClient, *stack_ids: str) -> None:
    """Make these imported Stacks (the mini Stack by default) the client's Learner's Active
    Stacks, as the onboarding screen does. Any other Stack is deactivated."""
    client.put(
        "/me/active-stacks", json={"stack_ids": list(stack_ids or ["mini-stack"])}
    ).raise_for_status()


def complete_lessons(
    session: Session, *lesson_ids: str, email: str = LEARNER_EMAIL, stack_id: str = "mini-stack"
) -> None:
    """Make these Completed Lessons for an onboarded Learner, the way passing a Lesson Quiz
    on the Stack's current Syllabus does (`progress.complete_lesson`)."""
    learner = session.scalars(select(Learner).where(Learner.email == email)).one()
    record = session.get(LearnerStack, (learner.id, stack_id))
    assert record is not None, f"{email} has never studied {stack_id}"
    version = session.scalars(
        select(Syllabus.version)
        .join(Stack, Stack.current_syllabus_pk == Syllabus.pk)
        .where(Stack.id == stack_id)
    ).one()
    for lesson_id in lesson_ids:
        progress.complete_lesson(session, record, lesson_id, datetime.now(UTC), version)


# --- A git repository: the baseline the Question Bank is held to --------------------------------


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repository holding the test Stack, committed: the baseline."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    write_bank(root, copy.deepcopy(BANK))
    commit(root)
    return root


def stack_dir(root: Path) -> Path:
    return root / "content" / "mini-stack"


def write_bank(root: Path, bank: dict[str, Any], **extra: dict[str, Any]) -> Path:
    return write_folder(root / "content", copy.deepcopy(SYLLABUS), {LESSON: bank, **extra})


def commit(root: Path) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "content")


def bank_now(root: Path) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(
        (stack_dir(root) / "question-bank" / f"{LESSON}.json").read_text(encoding="utf-8")
    )
    return doc
