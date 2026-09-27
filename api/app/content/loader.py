"""Read a Stack's content: one version folder (`syllabus.json`, and `changelog.json` if there
is one), the Stack's Question Bank (`<stack>/question-bank/*.json`, beside the versions) and its
Daily Challenges (`<stack>/challenges/`).

Each file is parsed into the format models (`app.content.format`). Anything that breaks the
format becomes a `Problem` naming the file and the item; rules that span several items are
checked afterwards by `app.content.check`.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from app.content.format import (
    ChallengeLaunch,
    Changelog,
    Concept,
    DailyChallenge,
    Lesson,
    Question,
    QuestionBank,
    Syllabus,
)

SYLLABUS_FILE = "syllabus.json"
CHANGELOG_FILE = "changelog.json"
QUESTION_BANK_DIR = "question-bank"
"""The Stack's Question Bank, `content/<stack-id>/question-bank/`: unversioned, beside the
Syllabus versions."""
LEGACY_QUESTIONS_DIR = "questions"
"""Where each version kept its own Question Banks before the bank became the Stack's (#15)."""
CHALLENGES_DIR = "challenges"
"""The Stack's Daily Challenges, `content/<stack-id>/challenges/`: unversioned, like the bank."""
LAUNCH_FILE = "launch.json"
"""In `challenges/`: the Day of Challenge #1. Every other file there is one Daily Challenge."""


def challenge_file_name(number: int) -> str:
    return f"{number:03}.json"


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
class Bank:
    """A Stack's Question Bank: every file of `question-bank/` that parses, in file-name order."""

    path: Path
    files: dict[Path, QuestionBank] = field(default_factory=dict)

    def concepts(self) -> list[tuple[Path, Concept]]:
        return [(p, c) for p, f in self.files.items() for c in f.concepts]

    def questions(self) -> list[tuple[Path, Question]]:
        return [(p, q) for p, f in self.files.items() for q in f.questions]

    def live_questions(self) -> list[Question]:
        """The Questions that aren't Retired Questions, in bank order: the ones that can be
        drawn."""
        return [q for _, q in self.questions() if q.retired is None]


@dataclass
class Challenges:
    """A Stack's Daily Challenges: its launch Day (None when `launch.json` is missing or doesn't
    parse) and every Challenge file that parses, in file-name order."""

    path: Path
    launch: ChallengeLaunch | None = None
    files: dict[Path, DailyChallenge] = field(default_factory=dict)

    def challenges(self) -> list[DailyChallenge]:
        return list(self.files.values())


@dataclass
class ContentFolder:
    path: Path
    syllabus: Syllabus
    bank: Bank
    """The Stack's Question Bank, which sits beside the version folders."""
    changelog: Changelog | None = None  # None when there is no changelog.json, or it's unreadable
    has_changelog_file: bool = False
    challenges: Challenges | None = None
    """The Stack's Daily Challenges, beside the version folders; None when it has none. Read
    only for an import (`check.load_checked_folder`)."""

    def lessons(self) -> list[Lesson]:
        return [lesson for week in self.syllabus.weeks for lesson in week.lessons]


def bank_dir(stack_dir: Path) -> Path:
    return stack_dir / QUESTION_BANK_DIR


def read_bank(stack_dir: Path) -> tuple[Bank, list[Problem]]:
    """Parse every file of the Stack's Question Bank. A file that breaks the format is left out
    and reported. A Stack with no `question-bank/` folder has an empty bank."""
    problems: list[Problem] = []
    bank = Bank(path=bank_dir(stack_dir))
    if bank.path.is_dir():
        for file in sorted(bank.path.glob("*.json")):
            parsed = _read(file, QuestionBank, problems)
            if parsed is not None:
                bank.files[file] = parsed
    return bank, problems


def read_challenges(stack_dir: Path) -> tuple[Challenges | None, list[Problem]]:
    """Parse the Stack's `challenges/` folder, or None if it has none. A file that breaks the
    format is left out and reported."""
    folder = stack_dir / CHALLENGES_DIR
    if not folder.is_dir():
        return None, []
    problems: list[Problem] = []
    challenges = Challenges(path=folder)
    launch = folder / LAUNCH_FILE
    if launch.exists():
        challenges.launch = _read(launch, ChallengeLaunch, problems)
    for file in sorted(folder.glob("*.json")):
        if file.name != LAUNCH_FILE:
            parsed = _read(file, DailyChallenge, problems)
            if parsed is not None:
                challenges.files[file] = parsed
    return challenges, problems


def read_folder(
    path: Path, bank: tuple[Bank, list[Problem]] | None = None
) -> tuple[ContentFolder | None, list[Problem]]:
    """Parse one version folder and the Stack's Question Bank (or the already read `bank`). The
    folder is None when `syllabus.json` itself can't be read."""
    problems: list[Problem] = []
    syllabus = _read(path / SYLLABUS_FILE, Syllabus, problems)
    the_bank, bank_problems = bank if bank is not None else read_bank(path.parent)
    problems += bank_problems
    if syllabus is None:
        return None, problems
    folder = ContentFolder(path=path, syllabus=syllabus, bank=the_bank)
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
