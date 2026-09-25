"""Read one version folder of a Stack: `syllabus.json` plus `questions/<lesson-id>.json`.

Each file is parsed into the format models (`app.content.format`). Anything that breaks the
format becomes a `Problem` naming the file and the item; rules that span several items are
checked afterwards by `app.content.check`.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from app.content.format import Lesson, QuestionBank, Syllabus

SYLLABUS_FILE = "syllabus.json"
QUESTIONS_DIR = "questions"


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
            Problem(
                "error", str(path), "/".join(str(p) for p in err["loc"]) or "(root)", err["msg"]
            )
            for err in e.errors()
        )
        return None
