import copy
import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base

LESSON = "w01-l01"


def _mc(n: int, concept: str) -> dict[str, Any]:
    return {
        "id": f"{LESSON}-q{n:02}",
        "concept": concept,
        "type": "multiple_choice",
        "prompt": f"Question {n}?",
        "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
        "answer": "a",
        "explanation": "Because.",
        "materials": ["mat-docs"],
    }


def _written(n: int, concept: str) -> dict[str, Any]:
    return {
        "id": f"{LESSON}-q{n:02}",
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

BANK: dict[str, Any] = {
    "schema_version": 1,
    "lesson_id": LESSON,
    "concepts": [{"id": f"concept-{c}", "name": f"Concept {c}"} for c in "abcd"],
    "questions": [
        _mc(1, "concept-a"),
        _mc(2, "concept-a"),
        _mc(3, "concept-b"),
        _mc(4, "concept-b"),
        _mc(5, "concept-c"),
        _mc(6, "concept-c"),
        _written(7, "concept-d"),
        _written(8, "concept-d"),
    ],
}


def write_folder(root: Path, syllabus: dict[str, Any], banks: dict[str, dict[str, Any]]) -> Path:
    folder = root / "mini-stack" / syllabus["version"]
    (folder / "questions").mkdir(parents=True, exist_ok=True)
    (folder / "syllabus.json").write_text(json.dumps(syllabus), encoding="utf-8")
    for name, bank in banks.items():
        (folder / "questions" / f"{name}.json").write_text(json.dumps(bank), encoding="utf-8")
    return folder


ContentFactory = Callable[..., Path]


@pytest.fixture
def make_content(tmp_path: Path) -> ContentFactory:
    """Write a valid folder; pass `edit(syllabus, bank)` to break it for a test."""

    def factory(edit: Callable[[dict, dict], None] | None = None) -> Path:
        syllabus, bank = copy.deepcopy(SYLLABUS), copy.deepcopy(BANK)
        if edit:
            edit(syllabus, bank)
        return write_folder(tmp_path, syllabus, {bank.get("lesson_id", LESSON): bank})

    return factory


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False)() as s:
        yield s
