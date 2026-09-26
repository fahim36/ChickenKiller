"""Move a Stack's Question Banks out of its version folders into the Stack's one Question Bank
(#15, ADR-0004). A one-time rewrite, allowed because nothing was released before it.

    content-migrate-bank <stack-folder> --sources <dir> [--dry-run] [--today YYYY-MM-DD]

- **Merge.** Every version's `questions/<lesson-id>.json` is read, oldest version first, so the
  newest version wins for a Concept or Question in several. Each Question is tagged to the Lesson
  of the file it was in, and written to `question-bank/<lesson-id>.json` for that Lesson, with
  the Concepts declared there. Every version's `questions/` folder is then removed.
- **Sources.** Each Question gets its Sources from the sidecar files in `--sources`, one per
  Lesson: `{"lesson_id": ..., "questions": {<question id>: {"sources": [...],
  "problem": null}}}`. A sidecar `problem` (a factual error found in the Question) retires the
  Question, with the problem as the reason and `--today` as the date. A Question with no Sources
  in any sidecar is written with none, which the content check refuses: the report lists them.
- **Changelogs.** The changelog now covers the Syllabus only (`app.content.diff`), so entries
  that only described a Question Bank are dropped: a Lesson listed as changed whose Syllabus
  fields didn't change, and any Concept or Question entry. The report lists them.

It refuses a Stack that already has a `question-bank/` folder. With `--dry-run` it writes
nothing and only prints the report. Run the content check afterwards.
"""

import argparse
import json
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from app.content.check import utc_today
from app.content.diff import diff_contents
from app.content.loader import (
    CHANGELOG_FILE,
    LEGACY_QUESTIONS_DIR,
    Bank,
    Problem,
    bank_dir,
    read_folder,
)
from app.content.versions import stack_versions

# The order a migrated Question's fields are written in.
_FIELD_ORDER = (
    "id",
    "lesson",
    "concept",
    "type",
    "prompt",
    "choices",
    "answer",
    "model_answer",
    "explanation",
    "materials",
    "sources",
    "retired",
)


@dataclass
class Report:
    questions: int = 0
    files: int = 0
    without_sources: list[str] = field(default_factory=list)
    retired: dict[str, str] = field(default_factory=dict)
    unknown_in_sidecars: list[str] = field(default_factory=list)
    dropped_changelog_entries: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        out = [
            f"{self.questions} Questions in {self.files} Question Bank files",
            f"{self.questions - len(self.without_sources)} with Sources, "
            f"{len(self.without_sources)} without",
        ]
        if self.without_sources:
            out.append("  without Sources: " + ", ".join(self.without_sources))
        out.append(f"{len(self.retired)} retired for a problem found in them")
        out += [f"  {qid}: {reason}" for qid, reason in self.retired.items()]
        if self.unknown_in_sidecars:
            out.append("sidecar entries for no Question: " + ", ".join(self.unknown_in_sidecars))
        out.append(f"{len(self.dropped_changelog_entries)} changelog entries dropped")
        out += [f"  {entry}" for entry in self.dropped_changelog_entries]
        return out


def migrate_bank(stack_dir: Path, sources_dir: Path, today: date, dry_run: bool = False) -> Report:
    """Rewrite one Stack folder into the Stack-level Question Bank. Raises FileExistsError if it
    already has one, and ValueError if it has no Question Banks to migrate."""
    target = bank_dir(stack_dir)
    if target.exists():
        raise FileExistsError(f"{target} already exists: the Stack is already migrated")
    versions = stack_versions(stack_dir)
    legacy = [v / LEGACY_QUESTIONS_DIR for v in versions if (v / LEGACY_QUESTIONS_DIR).is_dir()]
    if not legacy:
        raise ValueError(f"{stack_dir} has no version with a {LEGACY_QUESTIONS_DIR}/ folder")

    concepts: dict[str, tuple[str, dict[str, Any]]] = {}  # id -> (lesson, concept)
    questions: dict[str, tuple[str, dict[str, Any]]] = {}  # id -> (lesson, question)
    for folder in legacy:  # oldest first: the newest version wins
        for file in sorted(folder.glob("*.json")):
            doc = _load(file)
            lesson = doc["lesson_id"]
            for concept in doc["concepts"]:
                concepts.pop(concept["id"], None)
                concepts[concept["id"]] = (lesson, concept)
            for question in doc["questions"]:
                questions.pop(question["id"], None)
                questions[question["id"]] = (lesson, question)

    sidecars: dict[str, dict[str, Any]] = {}
    for file in sorted(sources_dir.glob("*.json")) if sources_dir.is_dir() else []:
        sidecars.update(_load(file).get("questions", {}))

    report = Report(questions=len(questions))
    report.unknown_in_sidecars = sorted(set(sidecars) - set(questions))
    files: dict[str, dict[str, Any]] = {}
    for lesson, concept in concepts.values():
        _file(files, lesson)["concepts"].append(concept)
    for qid, (lesson, question) in questions.items():
        found = sidecars.get(qid, {})
        migrated = {**question, "lesson": lesson, "sources": list(found.get("sources") or [])}
        if not migrated["sources"]:
            report.without_sources.append(qid)
        problem = found.get("problem")
        if problem:
            migrated["retired"] = {"reason": problem, "on": today.isoformat()}
            report.retired[qid] = problem
        _file(files, lesson)["questions"].append(
            {k: migrated[k] for k in _FIELD_ORDER if k in migrated}
        )
    report.files = len(files)

    changelogs = _trimmed_changelogs(versions, report)
    if dry_run:
        return report

    target.mkdir()
    for lesson, doc in sorted(files.items()):
        _write(target / f"{lesson}.json", doc)
    for path, doc in changelogs.items():
        _write(path, doc)
    for folder in legacy:
        shutil.rmtree(folder)
    return report


def _file(files: dict[str, dict[str, Any]], lesson: str) -> dict[str, Any]:
    return files.setdefault(lesson, {"schema_version": 2, "concepts": [], "questions": []})


def _trimmed_changelogs(versions: list[Path], report: Report) -> dict[Path, dict[str, Any]]:
    """Each changelog that needs entries dropped, as it will be written."""
    empty: tuple[Bank, list[Problem]] = (Bank(path=Path()), [])
    folders = [read_folder(v, empty)[0] for v in versions]
    rewritten: dict[Path, dict[str, Any]] = {}
    for i, folder in enumerate(folders):
        if folder is None or not (folder.path / CHANGELOG_FILE).is_file():
            continue
        previous = folders[i - 1] if i > 0 else None
        actual = {(c.kind.value, c.id): c.change for c in diff_contents(previous, folder)}
        doc = _load(folder.path / CHANGELOG_FILE)
        kept = []
        for entry in doc.get("changes", []):
            if actual.get((entry["kind"], entry["id"])) == entry["change"]:
                kept.append(entry)
            else:
                report.dropped_changelog_entries.append(
                    f"{folder.path.name}: {entry['change']} {entry['kind']} {entry['id']}"
                )
        if len(kept) != len(doc.get("changes", [])):
            rewritten[folder.path / CHANGELOG_FILE] = {**doc, "changes": kept}
    return rewritten


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Move a Stack's per-version Question Banks into its one Question Bank."
    )
    parser.add_argument("stack", type=Path, help="the Stack folder, content/<stack-id>")
    parser.add_argument("--sources", type=Path, required=True, help="the sidecar Sources folder")
    parser.add_argument("--dry-run", action="store_true", help="write nothing; print the report")
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=None,
        help="the UTC date for retirements (default: today)",
    )
    args = parser.parse_args(argv)
    try:
        report = migrate_bank(args.stack, args.sources, args.today or utc_today(), args.dry_run)
    except (FileExistsError, ValueError) as e:
        print(f"ERROR   {e}")
        return 1
    for line in report.lines():
        print(line)
    if not args.dry_run:
        print(f"wrote {bank_dir(args.stack)}; now run content-check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
