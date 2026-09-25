"""Read one version folder of a Stack: `syllabus.json` plus `questions/<lesson-id>.json`."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ContentFolder:
    path: Path
    syllabus: dict[str, Any]
    banks: dict[Path, dict[str, Any]] = field(default_factory=dict)

    def lessons(self) -> list[dict[str, Any]]:
        return [lesson for week in self.syllabus.get("weeks", []) for lesson in week["lessons"]]


def load_folder(path: Path) -> ContentFolder:
    """Parse every file in the folder. Raises `ValueError` naming the file on bad JSON."""
    syllabus = _read_json(path / "syllabus.json")
    folder = ContentFolder(path=path, syllabus=syllabus)
    questions_dir = path / "questions"
    if questions_dir.is_dir():
        for bank_path in sorted(questions_dir.glob("*.json")):
            folder.banks[bank_path] = _read_json(bank_path)
    return folder


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ValueError(f"{path}: file not found") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: invalid JSON at line {e.lineno}: {e.msg}") from e
