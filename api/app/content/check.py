"""The content check: run on a Stack version folder before committing it.

Errors fail the check; warnings are printed but don't. Usage:

    content-check <folder> [<folder> ...] [--links]

A folder is either one Stack version (it holds syllabus.json) or a content root, in which
case every <stack>/v* folder under it is checked.
"""

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from jsonschema import Draft202012Validator

from app.config import CONTENT_SCHEMA_DIR
from app.content.loader import ContentFolder, load_folder

# A Lesson Quiz is 4 multiple-choice + 2 written Questions; Retakes and Review Rounds
# need spare siblings, so a Question Bank holds 8-12.
BANK_MIN, BANK_MAX = 8, 12
QUIZ_MULTIPLE_CHOICE, QUIZ_WRITTEN = 4, 2
MIN_QUESTIONS_PER_CONCEPT = 2


@dataclass(frozen=True)
class Problem:
    level: str  # "error" or "warning"
    file: str
    item: str
    message: str

    def __str__(self) -> str:
        return f"{self.level.upper():7} {self.file} [{self.item}] {self.message}"


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((CONTENT_SCHEMA_DIR / name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _schema_problems(validator: Draft202012Validator, doc: Any, file: str) -> list[Problem]:
    return [
        Problem("error", file, "/".join(str(p) for p in e.absolute_path) or "(root)", e.message)
        for e in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    ]


def _duplicates(ids: Iterable[str]) -> list[str]:
    return [i for i, n in Counter(ids).items() if n > 1]


def check_folder(path: Path, links: bool = False) -> list[Problem]:
    try:
        folder = load_folder(path)
    except ValueError as e:
        return [Problem("error", str(path), "(file)", str(e))]

    syllabus_file = str(path / "syllabus.json")
    problems = _schema_problems(_validator("syllabus.schema.json"), folder.syllabus, syllabus_file)
    if problems:
        return problems  # the semantic checks below assume a well-formed syllabus

    problems += _check_syllabus(folder, syllabus_file)
    problems += _check_banks(folder)
    if links:
        problems += _check_links(folder.syllabus["materials"], syllabus_file)
    return problems


def _check_syllabus(folder: ContentFolder, file: str) -> list[Problem]:
    s = folder.syllabus
    problems: list[Problem] = []
    ids = [s["stack"]["id"], *(m["id"] for m in s["materials"])]
    for week in s["weeks"]:
        ids += [week["id"], *(x["id"] for x in week["lessons"] + week["milestones"])]
    for dup in _duplicates(ids):
        problems.append(Problem("error", file, dup, "duplicate permanent id"))

    numbers = [w["number"] for w in s["weeks"]]
    if numbers != list(range(1, len(numbers) + 1)):
        problems.append(
            Problem("error", file, "weeks", f"week numbers must run 1..n, got {numbers}")
        )

    material_ids = {m["id"] for m in s["materials"]}
    for week in s["weeks"]:
        for item in week["lessons"] + week["milestones"]:
            for ref in item["materials"]:
                if ref not in material_ids:
                    problems.append(Problem("error", file, item["id"], f"unknown material '{ref}'"))
    return problems


def _check_banks(folder: ContentFolder) -> list[Problem]:
    problems: list[Problem] = []
    validator = _validator("question-bank.schema.json")
    lesson_ids = {lesson["id"] for lesson in folder.lessons()}
    material_ids = {m["id"] for m in folder.syllabus["materials"]}
    seen_concepts: list[str] = []
    seen_questions: list[str] = []
    banked: set[str] = set()

    for bank_path, bank in folder.banks.items():
        file = str(bank_path)
        schema_problems = _schema_problems(validator, bank, file)
        if schema_problems:
            problems += schema_problems
            continue

        lesson_id = bank["lesson_id"]
        banked.add(lesson_id)
        if bank_path.stem != lesson_id:
            problems.append(Problem("error", file, lesson_id, "file name must be <lesson_id>.json"))
        if lesson_id not in lesson_ids:
            problems.append(Problem("error", file, lesson_id, "lesson_id is not in the Syllabus"))

        concept_ids = [c["id"] for c in bank["concepts"]]
        seen_concepts += concept_ids
        questions = bank["questions"]
        seen_questions += [q["id"] for q in questions]

        per_concept = Counter(q["concept"] for q in questions)
        for q in questions:
            if q["concept"] not in concept_ids:
                problems.append(
                    Problem("error", file, q["id"], f"unknown concept '{q['concept']}'")
                )
            for ref in q["materials"]:
                if ref not in material_ids:
                    problems.append(Problem("error", file, q["id"], f"unknown material '{ref}'"))
            if q["type"] == "multiple_choice":
                choice_ids = [c["id"] for c in q["choices"]]
                if _duplicates(choice_ids):
                    problems.append(Problem("error", file, q["id"], "duplicate choice ids"))
                if q["answer"] not in choice_ids:
                    problems.append(
                        Problem("error", file, q["id"], "answer is not one of the choices")
                    )
        for concept in concept_ids:
            if per_concept[concept] < MIN_QUESTIONS_PER_CONCEPT:
                problems.append(
                    Problem(
                        "error",
                        file,
                        concept,
                        f"Concept has {per_concept[concept]} Question(s); needs at least "
                        f"{MIN_QUESTIONS_PER_CONCEPT} so a Retake always has a sibling",
                    )
                )

        if not BANK_MIN <= len(questions) <= BANK_MAX:
            problems.append(
                Problem(
                    "error",
                    file,
                    lesson_id,
                    f"Question Bank has {len(questions)} Questions; needs {BANK_MIN}-{BANK_MAX}",
                )
            )
        types = Counter(q["type"] for q in questions)
        mc, written = types["multiple_choice"], types["written"]
        if mc < QUIZ_MULTIPLE_CHOICE or written < QUIZ_WRITTEN:
            problems.append(
                Problem(
                    "error",
                    file,
                    lesson_id,
                    f"a Lesson Quiz needs {QUIZ_MULTIPLE_CHOICE} multiple-choice and "
                    f"{QUIZ_WRITTEN} written Questions; bank has {mc} and {written}",
                )
            )

    for dup in _duplicates(seen_concepts):
        problems.append(
            Problem("error", str(folder.path / "questions"), dup, "duplicate concept id")
        )
    for dup in _duplicates(seen_questions):
        problems.append(
            Problem("error", str(folder.path / "questions"), dup, "duplicate question id")
        )

    missing = sorted(lesson_ids - banked)
    if missing:
        problems.append(
            Problem(
                "warning",
                str(folder.path / "questions"),
                f"{len(missing)} lessons",
                f"no Question Bank yet (first: {', '.join(missing[:3])})",
            )
        )
    return problems


# 401/403/429 usually mean the site blocks automated requests, not that the link is dead.
_BLOCKED = {401, 403, 429}


def _check_links(materials: list[dict[str, Any]], file: str) -> list[Problem]:
    headers = {"User-Agent": "Mozilla/5.0 (content-check; +learning-app)"}

    def probe(m: dict[str, Any]) -> Problem | None:
        try:
            with httpx.Client(follow_redirects=True, timeout=20, headers=headers) as client:
                r = client.get(m["url"])
        except httpx.HTTPError as e:
            return Problem("error", file, m["id"], f"link doesn't load: {type(e).__name__}")
        if r.status_code in _BLOCKED:
            return Problem(
                "warning", file, m["id"], f"site refused the check (HTTP {r.status_code})"
            )
        if r.status_code >= 400:
            return Problem("error", file, m["id"], f"link doesn't load: HTTP {r.status_code}")
        return None

    with ThreadPoolExecutor(max_workers=16) as pool:
        return [p for p in pool.map(probe, materials) if p]


def _version_folders(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if (path / "syllabus.json").exists():
            found.append(path)
        else:
            found += sorted(p for p in path.glob("*/v*") if p.is_dir())
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Stack content folders before commit.")
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument("--links", action="store_true", help="also check every Material link loads")
    args = parser.parse_args(argv)

    folders = _version_folders(args.folders)
    if not folders:
        print("no Stack version folders found")
        return 1

    errors = 0
    for folder in folders:
        problems = check_folder(folder, links=args.links)
        for p in problems:
            print(p)
        n = sum(p.level == "error" for p in problems)
        errors += n
        print(f"{folder}: {'OK' if n == 0 else f'{n} error(s)'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
