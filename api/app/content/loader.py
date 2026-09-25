"""Read one version folder of a Stack: `syllabus.json`, `questions/<lesson-id>.json`, and
`changelog.json` if there is one.

Each file is parsed into the format models (`app.content.format`). Anything that breaks the
format becomes a `Problem` naming the file and the item; rules that span several items are
checked afterwards by `app.content.check`.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from app.content.format import Changelog, Lesson, QuestionBank, Syllabus

SYLLABUS_FILE = "syllabus.json"
QUESTIONS_DIR = "questions"
CHANGELOG_FILE = "changelog.json"


@dataclass(frozen=True)
class Problem:
    level: Literal["error", "warning"]
    file: str
    item: str
    message: str

    def __str__(self) -> str:
        return f"{self.level.upper():7} {self.file} [{self.item}] {self.message}"


class ContentError(Exception):
    """A content folder can't be used. Carries every error found."""

    def __init__(self, problems: list[Problem]) -> None:
        self.problems = problems
        super().__init__("\n".join(str(p) for p in problems))


@dataclass
class ContentFolder:
    path: Path
    syllabus: Syllabus
    banks: dict[Path, QuestionBank] = field(default_factory=dict)
    changelog: Changelog | None = None  # None when there is no changelog.json, or it's unreadable
    has_changelog_file: bool = False

    def lessons(self) -> list[Lesson]:
        return [lesson for week in self.syllabus.weeks for lesson in week.lessons]


def read_folder(path: Path) -> tuple[ContentFolder | None, list[Problem]]:
    """Parse every file. The folder is None when `syllabus.json` itself can't be read; a Question
    Bank that breaks the format is left out and reported."""
    problems: list[Problem] = []
    syllabus = _read(path / SYLLABUS_FILE, Syllabus, problems)
    if syllabus is None:
        return None, problems
    folder = ContentFolder(path=path, syllabus=syllabus)
    questions_dir = path / QUESTIONS_DIR
    if questions_dir.is_dir():
        for bank_path in sorted(questions_dir.glob("*.json")):
            bank = _read(bank_path, QuestionBank, problems)
            if bank is not None:
                folder.banks[bank_path] = bank
    changelog_path = path / CHANGELOG_FILE
    if changelog_path.exists():
        folder.has_changelog_file = True
        folder.changelog = _read(changelog_path, Changelog, problems)
    return folder, problems


def _read[M: BaseModel](path: Path, model: type[M], problems: list[Problem]) -> M | None:
    try:
        doc: Any = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problems.append(Problem("error", str(path), "(file)", "file not found"))
        return None
    except json.JSONDecodeError as e:
        problems.append(
            Problem("error", str(path), "(file)", f"invalid JSON at line {e.lineno}: {e.msg}")
        )
        return None
    try:
        return model.model_validate(doc)
    except ValidationError as e:
        problems.extend(
            _format_problem(str(path), doc, err["loc"], err["msg"]) for err in e.errors()
        )
        return None


def _format_problem(file: str, doc: Any, loc: tuple[int | str, ...], msg: str) -> Problem:
    """Name the item by the permanent ID of the innermost object around the error (such as the
    Question), with the path to the field in the message; outside any item, name the field."""
    where = "/".join(str(p) for p in loc)
    item_id = None
    node = doc
    for i, part in enumerate(loc):
        in_choices = i >= 2 and loc[i - 2] == "choices"  # a Choice's id is a letter, not an item
        if isinstance(node, dict) and isinstance(node.get("id"), str) and not in_choices:
            item_id = node["id"]
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and isinstance(part, int) and 0 <= part < len(node):
            node = node[part]
        elif isinstance(part, int) or isinstance(node, list):
            break
        # else: a union tag such as "multiple_choice", which isn't a key in the file
    if item_id is None:
        return Problem("error", file, where or "(root)", msg)
    return Problem("error", file, item_id, f"{where}: {msg}")
