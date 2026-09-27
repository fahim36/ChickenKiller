"""Start a new Syllabus version: the first step of a Syllabus Update.

    content-new-version <stack-id> [--content DIR] [--version vYYYY-MM-DD[.N]]

Copies the Stack's newest version folder to a new one named for today (`app.content.versions`),
changing only the `version` in `syllabus.json`. Edits then go into the copy, so every item the
update leaves alone keeps its permanent ID by construction. A committed version is never edited:
the importer refuses changed content under a version it has already imported.

It also starts the new version's `changelog.json`, naming the version it follows, with an empty
`summary` and no `changes`: the content check fails until the update fills them in.

The Question Bank is not copied: it is the Stack's, beside the versions
(`content/<stack-id>/question-bank/`), and a Syllabus Update adds to it in place (ADR-0004).

A Stack with no versions yet gets a folder with only the changelog, and an empty
`question-bank/`; write `syllabus.json` into it from scratch. Prints the new folder's path.
"""

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

from app.config import CONTENT_DIR
from app.content.loader import CHANGELOG_FILE, SYLLABUS_FILE, bank_dir
from app.content.versions import next_version, stack_versions, validate_version, version_key


def new_version(content_dir: Path, stack_id: str, today: date, version: str | None = None) -> Path:
    """Create the new version folder and return its path."""
    stack_dir = content_dir / stack_id
    existing = stack_versions(stack_dir)
    name = validate_version(version) if version else next_version([p.name for p in existing], today)
    target = stack_dir / name
    if target.exists():
        raise FileExistsError(f"{target} already exists; a version is never edited in place")
    if existing and version_key(name) < version_key(existing[-1].name):
        raise ValueError(f"{name} would sort before the newest version, {existing[-1].name}")
    previous = existing[-1].name if existing else None
    stub = {
        "schema_version": 1,
        "version": name,
        "previous_version": previous,
        "summary": "",
        "changes": [],
    }

    if not existing:
        target.mkdir(parents=True)
        bank_dir(stack_dir).mkdir(exist_ok=True)
        _write_json(target / CHANGELOG_FILE, stub)
        return target

    source = existing[-1]
    # The changelog belongs to the version it describes; the new version writes its own.
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(CHANGELOG_FILE))
    syllabus = target / SYLLABUS_FILE
    text = syllabus.read_bytes().decode("utf-8")  # bytes, so line endings stay as they are
    pattern = re.compile(r'("version"\s*:\s*)"' + re.escape(source.name) + '"')
    new_text, count = pattern.subn(lambda m: f'{m[1]}"{name}"', text, count=1)
    if count != 1:
        shutil.rmtree(target)
        raise ValueError(f"{source / SYLLABUS_FILE}: its version isn't {source.name!r}")
    syllabus.write_bytes(new_text.encode("utf-8"))
    _write_json(target / CHANGELOG_FILE, stub)
    return target


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy a Stack's newest version folder to a new version, to edit."
    )
    parser.add_argument("stack", help="the Stack id, which is its folder name under content/")
    parser.add_argument("--content", type=Path, default=CONTENT_DIR, help="the content root")
    parser.add_argument("--version", help="the new version name (default: today's)")
    args = parser.parse_args(argv)
    try:
        target = new_version(args.content, args.stack, date.today(), args.version)
    except (FileExistsError, ValueError) as e:
        print(f"ERROR   {e}")
        return 1
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
