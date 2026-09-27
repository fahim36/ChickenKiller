"""The committed content (#12): every Stack in `content/` has Questions for every Lesson of its
newest Syllabus, enough for a Lesson Quiz, and imports with them. The content check only warns
about a Lesson with no Questions at all, so this holds the committed Stacks to more."""

from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import REPO_ROOT
from app.content.check import LESSON_MIN, QUIZ_MULTIPLE_CHOICE, QUIZ_WRITTEN
from app.content.importer import import_folder
from app.content.loader import read_bank, read_folder
from app.content.versions import stack_versions
from app.models import Lesson, Stack
from tests.conftest import onboard

STACKS = sorted(p for p in (REPO_ROOT / "content").iterdir() if p.name != "schema")


@pytest.mark.parametrize("stack_dir", STACKS, ids=lambda p: p.name)
def test_every_lesson_of_the_newest_version_has_enough_questions(stack_dir: Path) -> None:
    bank, _ = read_bank(stack_dir)
    folder, problems = read_folder(stack_versions(stack_dir)[-1], (bank, []))
    assert folder is not None, problems
    live: dict[str, Counter[str]] = {lesson.id: Counter() for lesson in folder.lessons()}
    for question in bank.live_questions():
        if question.lesson in live:
            live[question.lesson][question.type] += 1

    short = {
        lesson: dict(types)
        for lesson, types in live.items()
        if types.total() < LESSON_MIN
        or types["multiple_choice"] < QUIZ_MULTIPLE_CHOICE
        or types["written"] < QUIZ_WRITTEN
    }
    assert short == {}


@pytest.mark.parametrize("stack_dir", STACKS, ids=lambda p: p.name)
def test_the_stack_imports_with_questions_for_every_lesson(
    session: Session, api: TestClient, stack_dir: Path
) -> None:
    for version in stack_versions(stack_dir):
        import_folder(session, version)

    stack = session.get(Stack, stack_dir.name)
    assert stack is not None and stack.current_syllabus is not None
    lessons = session.scalars(
        select(Lesson).where(Lesson.syllabus_pk == stack.current_syllabus.pk)
    ).all()
    assert lessons
    assert [x.id for x in lessons if len(x.question_ids) < LESSON_MIN] == []

    onboard(api, stack.id)
    assert stack.id in [s["id"] for s in api.get("/stacks").json()]
