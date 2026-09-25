"""The content check: run on a Stack version folder before committing it.

Errors fail the check; warnings are printed but don't. Usage:

    content-check <folder> [<folder> ...] [--links]

A folder is either one Stack version (it holds syllabus.json) or a content root, in which
case every <stack>/v* folder under it is checked. The format itself is the Pydantic models in
`app.content.format`; this module adds the rules that span several items.
"""

import argparse
import sys
from collections import Counter
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from app.content.format import Lesson, Material, Milestone, MultipleChoiceQuestion
from app.content.loader import (
    QUESTIONS_DIR,
    SYLLABUS_FILE,
    ContentError,
    ContentFolder,
    Problem,
    read_folder,
)

__all__ = ["Problem", "check_folder", "load_checked_folder", "main", "version_folders"]

# A Lesson Quiz is 4 multiple-choice + 2 written Questions; Retakes and Review Rounds
# need spare siblings, so a Question Bank holds 8-12.
BANK_MIN, BANK_MAX = 8, 12
QUIZ_MULTIPLE_CHOICE, QUIZ_WRITTEN = 4, 2
MIN_QUESTIONS_PER_CONCEPT = 2


def _duplicates(ids: Iterable[str]) -> list[str]:
    return [i for i, n in Counter(ids).items() if n > 1]


def check_folder(path: Path, links: bool = False) -> list[Problem]:
    folder, problems = read_folder(path)
    if folder is None:
        return problems  # the rules below assume a well-formed syllabus
    return problems + _check_parsed(folder, links=links)


def load_checked_folder(path: Path) -> ContentFolder:
    """The folder, if it passes the check (links aside). Raises `ContentError` otherwise."""
    folder, problems = read_folder(path)
    if folder is not None:
        problems += _check_parsed(folder, links=False)
    errors = [p for p in problems if p.level == "error"]
    if errors or folder is None:
        raise ContentError(errors)
    return folder


def _check_parsed(folder: ContentFolder, links: bool) -> list[Problem]:
    syllabus_file = str(folder.path / SYLLABUS_FILE)
    problems = _check_syllabus(folder, syllabus_file) + _check_banks(folder)
    if links:
        problems += _check_links(folder.syllabus.materials, syllabus_file)
    return problems


def _check_syllabus(folder: ContentFolder, file: str) -> list[Problem]:
    s = folder.syllabus
    problems: list[Problem] = []
    ids = [s.stack.id, *(m.id for m in s.materials)]
    for week in s.weeks:
        ids += [week.id, *(x.id for x in week.lessons), *(x.id for x in week.milestones)]
    for dup in _duplicates(ids):
        problems.append(Problem("error", file, dup, "duplicate permanent id"))

    numbers = [w.number for w in s.weeks]
    if numbers != list(range(1, len(numbers) + 1)):
        problems.append(
            Problem("error", file, "weeks", f"week numbers must run 1..n, got {numbers}")
        )

    material_ids = {m.id for m in s.materials}
    for week in s.weeks:
        items: list[Lesson | Milestone] = [*week.lessons, *week.milestones]
        for item in items:
            for ref in item.materials:
                if ref not in material_ids:
                    problems.append(Problem("error", file, item.id, f"unknown material '{ref}'"))
    return problems


def _check_banks(folder: ContentFolder) -> list[Problem]:
    problems: list[Problem] = []
    lesson_ids = {lesson.id for lesson in folder.lessons()}
    material_ids = {m.id for m in folder.syllabus.materials}
    seen_concepts: list[str] = []
    seen_questions: list[str] = []
    banked: set[str] = set()

    for bank_path, bank in folder.banks.items():
        file = str(bank_path)
        lesson_id = bank.lesson_id
        banked.add(lesson_id)
        if bank_path.stem != lesson_id:
            problems.append(Problem("error", file, lesson_id, "file name must be <lesson_id>.json"))
        if lesson_id not in lesson_ids:
            problems.append(Problem("error", file, lesson_id, "lesson_id is not in the Syllabus"))

        concept_ids = [c.id for c in bank.concepts]
        seen_concepts += concept_ids
        questions = bank.questions
        seen_questions += [q.id for q in questions]

        per_concept = Counter(q.concept for q in questions)
        for q in questions:
            if q.concept not in concept_ids:
                problems.append(Problem("error", file, q.id, f"unknown concept '{q.concept}'"))
            for ref in q.materials:
                if ref not in material_ids:
                    problems.append(Problem("error", file, q.id, f"unknown material '{ref}'"))
            if isinstance(q, MultipleChoiceQuestion):
                choice_ids = [c.id for c in q.choices]
                if _duplicates(choice_ids):
                    problems.append(Problem("error", file, q.id, "duplicate choice ids"))
                if q.answer not in choice_ids:
                    problems.append(
                        Problem("error", file, q.id, "answer is not one of the choices")
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
        types = Counter(q.type for q in questions)
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

    questions_dir = str(folder.path / QUESTIONS_DIR)
    for dup in _duplicates(seen_concepts):
        problems.append(Problem("error", questions_dir, dup, "duplicate concept id"))
    for dup in _duplicates(seen_questions):
        problems.append(Problem("error", questions_dir, dup, "duplicate question id"))

    missing = sorted(lesson_ids - banked)
    if missing:
        problems.append(
            Problem(
                "warning",
                questions_dir,
                f"{len(missing)} lessons",
                f"no Question Bank yet (first: {', '.join(missing[:3])})",
            )
        )
    return problems


# 401/403/429 usually mean the site blocks automated requests, not that the link is dead.
_BLOCKED = {401, 403, 429}


def _check_links(materials: list[Material], file: str) -> list[Problem]:
    headers = {"User-Agent": "Mozilla/5.0 (content-check; +learning-app)"}

    def probe(m: Material) -> Problem | None:
        try:
            with httpx.Client(follow_redirects=True, timeout=20, headers=headers) as client:
                r = client.get(m.url)
        except httpx.HTTPError as e:
            return Problem("error", file, m.id, f"link doesn't load: {type(e).__name__}")
        if r.status_code in _BLOCKED:
            return Problem("warning", file, m.id, f"site refused the check (HTTP {r.status_code})")
        if r.status_code >= 400:
            return Problem("error", file, m.id, f"link doesn't load: HTTP {r.status_code}")
        return None

    with ThreadPoolExecutor(max_workers=16) as pool:
        return [p for p in pool.map(probe, materials) if p]


def version_folders(paths: list[Path]) -> list[Path]:
    """Each path as a Stack version folder, or every <stack>/v* folder under a content root."""
    found: list[Path] = []
    for path in paths:
        if (path / SYLLABUS_FILE).exists():
            found.append(path)
        else:
            found += sorted(p for p in path.glob("*/v*") if p.is_dir())
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Stack content folders before commit.")
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument("--links", action="store_true", help="also check every Material link loads")
    args = parser.parse_args(argv)

    folders = version_folders(args.folders)
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
