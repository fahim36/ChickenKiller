"""A Stack's Question Bank as committed: the baseline the content check holds the bank to.

"Committed" means a git ref, `HEAD` by default (what the pre-commit hook needs); CI passes a pull
request's base. Relative to it, a committed Question is never deleted, and never changes except
by being retired or re-tagged to another Lesson (ADR-0004). The rules themselves are in
`app.content.check`; this module only reads the baseline out of git.

- The bank is read from `<stack>/question-bank/*.json` at the ref.
- A ref from before the bank became the Stack's (#15) has the old layout instead, one bank per
  Lesson in each version folder (`<stack>/<version>/questions/<lesson-id>.json`). Those banks are
  merged, the newest version winning, and each Question is tagged to its file's Lesson. Their
  Questions had no Sources, so they may gain Sources once (`BaselineQuestion.legacy`).
- The Stack's Daily Challenges (`<stack>/challenges/<number>.json`) are read as committed bytes:
  one whose Day has passed is frozen (the rule is in `app.content.check` too).
- A Stack the ref doesn't have yet has an empty baseline: every Question is new.
- Outside a git repository there is no baseline (`BaselineUnavailable`), and the rules that need
  one are skipped.
"""

import json
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.content.format import DailyChallenge, Question, Retirement
from app.content.loader import CHALLENGES_DIR, LAUNCH_FILE, LEGACY_QUESTIONS_DIR, QUESTION_BANK_DIR
from app.content.versions import is_version, version_key

_QUESTION: TypeAdapter[Any] = TypeAdapter(Question)


class BaselineUnavailable(Exception):
    """There is no git baseline to compare with: not a git repository, or no git."""


class BadBaseline(Exception):
    """The baseline ref doesn't name a commit."""


@dataclass(frozen=True)
class BaselineQuestion:
    id: str
    concept: str
    lesson: str | None
    """The Lesson it was tagged to; it may change (a re-tag)."""
    fields: dict[str, Any]
    """Everything that may never change: the Question without `lesson` and `retired`."""
    retired: dict[str, Any] | None
    file: str
    """Where it was committed, relative to the Stack folder."""
    legacy: bool
    """Committed in the old layout, before Questions had Sources: it may gain them once."""


@dataclass(frozen=True)
class BaselineChallenge:
    file: str
    """Where it was committed, relative to the Stack folder."""
    content: bytes
    """The file as committed, with LF line endings: a released Challenge never changes."""
    date: date | None
    """Its Day as committed; None if the file didn't parse."""
    number: int | None


@dataclass(frozen=True)
class Baseline:
    ref: str
    questions: dict[str, BaselineQuestion]
    challenges: dict[str, BaselineChallenge] = field(default_factory=dict)
    """Keyed by file name, such as `001.json`."""


def normalise_newlines(content: bytes) -> bytes:
    """Line endings don't count (a Windows checkout may have CRLF)."""
    return content.replace(b"\r\n", b"\n")


def question_fields(question: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """A Question (as JSON) split into what may never change and its retirement, normalised
    through the format when it parses, so formatting and stated defaults don't count."""
    try:
        doc = _QUESTION.dump_python(_QUESTION.validate_python(question), mode="json")
    except ValidationError:
        doc = dict(question)
    doc.pop("lesson", None)
    retired = doc.pop("retired", None)
    if isinstance(retired, dict):
        try:
            retired = Retirement.model_validate(retired).model_dump(mode="json")
        except ValidationError:
            pass
    return doc, retired


def read_baseline(stack_dir: Path, ref: str = "HEAD") -> Baseline:
    """The Stack's Question Bank at `ref`. Raises BaselineUnavailable or BadBaseline."""
    stack_dir = stack_dir.resolve()
    try:
        top = _git(stack_dir, "rev-parse", "--show-toplevel").strip()
    except (OSError, subprocess.CalledProcessError) as e:
        raise BaselineUnavailable(f"{stack_dir} is not in a git repository") from e
    root = Path(top).resolve()
    try:
        prefix = PurePosixPath(stack_dir.relative_to(root).as_posix())
    except ValueError as e:
        raise BaselineUnavailable(f"{stack_dir} is outside its git work tree {root}") from e
    try:
        commit = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").strip()
    except subprocess.CalledProcessError:
        if ref == "HEAD" and not _git(root, "rev-list", "-n", "1", "--all").strip():
            return Baseline(ref, {})  # a repository with no commits yet: nothing is committed
        raise BadBaseline(f"git ref {ref!r} doesn't name a commit") from None

    names = _git(root, "ls-tree", "-r", "--name-only", commit, "--", f"{prefix}/").splitlines()
    bank_files, legacy_files, challenge_files = [], [], []
    for name in names:
        path = PurePosixPath(name)
        depth = len(path.parts) - len(prefix.parts)
        if path.suffix != ".json":
            continue
        if depth == 2 and path.parent.name == QUESTION_BANK_DIR:
            bank_files.append(path)
        elif depth == 2 and path.parent.name == CHALLENGES_DIR and path.name != LAUNCH_FILE:
            challenge_files.append(path)
        elif (
            depth == 3
            and path.parent.name == LEGACY_QUESTIONS_DIR
            and is_version(path.parent.parent.name)
        ):
            legacy_files.append(path)

    challenges = {
        path.name: _challenge(path.relative_to(prefix).as_posix(), content)
        for path, content in _cat(root, commit, challenge_files).items()
    }
    questions: dict[str, BaselineQuestion] = {}
    if bank_files:
        contents = _cat(root, commit, bank_files)
        for path in bank_files:
            doc = _json(contents[path])
            for q in doc.get("questions", []) if isinstance(doc, dict) else []:
                _add(questions, q, path.relative_to(prefix).as_posix(), legacy=False)
        return Baseline(ref, questions, challenges)

    # The old layout: newest version last, so it wins.
    legacy_files.sort(key=lambda p: (version_key(p.parent.parent.name), p.name))
    contents = _cat(root, commit, legacy_files)
    for path in legacy_files:
        doc = _json(contents[path])
        if not isinstance(doc, dict):
            continue
        for q in doc.get("questions", []):
            if isinstance(q, dict):
                _add(
                    questions,
                    {**q, "lesson": doc.get("lesson_id")},
                    path.relative_to(prefix).as_posix(),
                    legacy=True,
                )
    return Baseline(ref, questions, challenges)


def _challenge(file: str, content: bytes) -> BaselineChallenge:
    try:
        parsed: DailyChallenge | None = DailyChallenge.model_validate(_json(content))
    except ValidationError:
        parsed = None
    return BaselineChallenge(
        file,
        normalise_newlines(content),
        parsed.date if parsed else None,
        parsed.number if parsed else None,
    )


def _add(into: dict[str, BaselineQuestion], q: Any, file: str, legacy: bool) -> None:
    if not isinstance(q, dict) or not isinstance(q.get("id"), str):
        return
    fields, retired = question_fields(q)
    lesson = q.get("lesson")
    into[q["id"]] = BaselineQuestion(
        q["id"],
        str(q.get("concept")),
        lesson if isinstance(lesson, str) else None,
        fields,
        retired,
        file,
        legacy,
    )


def _json(data: bytes) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, check=True, text=True, encoding="utf-8"
    ).stdout


def _cat(root: Path, commit: str, paths: list[PurePosixPath]) -> dict[PurePosixPath, bytes]:
    """Every file's contents at `commit`, in one `git cat-file --batch`."""
    if not paths:
        return {}
    request = "".join(f"{commit}:{p}\n" for p in paths).encode("utf-8")
    out = subprocess.run(
        ["git", "cat-file", "--batch"], cwd=root, input=request, capture_output=True, check=True
    ).stdout
    contents: dict[PurePosixPath, bytes] = {}
    at = 0
    for path in paths:
        end = out.index(b"\n", at)
        header = out[at:end].split()
        size = int(header[2])
        contents[path] = out[end + 1 : end + 1 + size]
        at = end + 1 + size + 1
    return contents
