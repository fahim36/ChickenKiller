"""Publish the content format as JSON Schema files in `content/schema/`.

    content-schema            # rewrite the files from the models in app.content.format
    content-schema --check    # fail if the committed files are out of date

Claude Code reads these files when it writes content; a test keeps them in step with the models.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import CONTENT_SCHEMA_DIR
from app.content.format import ChallengeLaunch, Changelog, DailyChallenge, QuestionBank, Syllabus

_DIALECT = "https://json-schema.org/draft/2020-12/schema"
_MODELS: dict[str, type[BaseModel]] = {
    "syllabus.schema.json": Syllabus,
    "question-bank.schema.json": QuestionBank,
    "changelog.schema.json": Changelog,
    "challenge.schema.json": DailyChallenge,
    "challenge-launch.schema.json": ChallengeLaunch,
}


def json_schema_files() -> dict[str, str]:
    """File name -> file contents, exactly as they should be committed."""
    return {name: _render(name, model) for name, model in _MODELS.items()}


def _render(name: str, model: type[BaseModel]) -> str:
    schema: dict[str, Any] = {"$schema": _DIALECT, "$id": name, **model.model_json_schema()}
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def stale_schema_files(directory: Path = CONTENT_SCHEMA_DIR) -> list[str]:
    """Files that differ from the models, compared as JSON so line endings don't count."""
    stale = []
    for name, text in json_schema_files().items():
        path = directory / name
        if not path.exists() or json.loads(path.read_text(encoding="utf-8")) != json.loads(text):
            stale.append(name)
    return stale


def write_schema_files(directory: Path = CONTENT_SCHEMA_DIR) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in json_schema_files().items():
        path = directory / name
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the content format's JSON Schema files.")
    parser.add_argument("--check", action="store_true", help="fail if the files are out of date")
    args = parser.parse_args(argv)
    if args.check:
        stale = stale_schema_files()
        if stale:
            print(f"out of date in {CONTENT_SCHEMA_DIR}: {', '.join(stale)}; run content-schema")
            return 1
        print(f"{CONTENT_SCHEMA_DIR} is up to date")
        return 0
    for path in write_schema_files():
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
