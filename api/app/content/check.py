"""The content check: run on a Stack's content before committing it.

Errors fail the check; warnings are printed but don't. Usage:

    content-check <folder> [<folder> ...] [--links] [--baseline REF] [--today YYYY-MM-DD]

A folder is a content root, a Stack folder (`content/<stack-id>/`) or one of its version
folders; each Stack found is checked whole: every Syllabus version, and the Stack's Question
Bank. The format itself is the Pydantic models in `app.content.format`; this module adds the
rules that span several items.

**The Question Bank** is checked against the Stack's newest Syllabus version: a Question's
Lesson tag and Materials resolve there. It is also held to what is committed, the git
`--baseline` (default `HEAD`, which is what the pre-commit hook needs; CI passes a pull
request's base), read by `app.content.baseline`:

- a committed Question is never deleted, and never changes except by adding `retired` or
  changing its Lesson tag; a retirement is never undone or edited;
- a Question new since the baseline has every Source accessed in the current run: today or
  yesterday in UTC, by the `today` passed in, so a run that crosses 00:00 UTC still passes;
- a new Question whose Concept already has committed Questions is a warning naming one of them.

With no git baseline (content outside a git repository) those rules are skipped, with a warning
that says so.
"""

import argparse
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx

from app.content.baseline import BadBaseline, BaselineUnavailable, question_fields, read_baseline
from app.content.diff import diff_contents
from app.content.format import ItemKind, Lesson, Material, Milestone, MultipleChoiceQuestion
from app.content.loader import (
    CHANGELOG_FILE,
    LEGACY_QUESTIONS_DIR,
    QUESTION_BANK_DIR,
    SYLLABUS_FILE,
    Bank,
    ContentError,
    ContentFolder,
    Problem,
    read_bank,
    read_folder,
)
from app.content.versions import (
    VersionKey,
    earlier_versions,
    is_version,
    stack_versions,
    version_key,
)

__all__ = [
    "Problem",
    "check_folder",
    "check_stack",
    "load_checked_folder",
    "main",
    "stack_folders",
    "version_folders",
]

# A Lesson Quiz is 4 multiple-choice + 2 written Questions; Retakes and Review need spare
# siblings, so each Lesson has at least 8 Questions that aren't retired. The bank only grows, so
# there is no maximum.
LESSON_MIN = 8
QUIZ_MULTIPLE_CHOICE, QUIZ_WRITTEN = 4, 2
MIN_QUESTIONS_PER_CONCEPT = 2


def _duplicates(ids: Iterable[str]) -> list[str]:
    return [i for i, n in Counter(ids).items() if n > 1]


def utc_today() -> date:
    return datetime.now(UTC).date()


def check_folder(
    path: Path,
    links: bool = False,
    *,
    baseline: str | None = "HEAD",
    today: date | None = None,
) -> list[Problem]:
    """Check one version folder, and its Stack's Question Bank (against the Stack's newest
    version). `baseline` is the git ref the bank is held to; None skips those rules. `today`
    (UTC) is the clock for new Questions' Sources."""
    bank, bank_problems = read_bank(path.parent)
    return (
        _check_version(path, bank, links)
        + bank_problems
        + _check_bank(path.parent, bank, baseline, today or utc_today())
    )


def check_stack(
    stack_dir: Path,
    links: bool = False,
    *,
    baseline: str | None = "HEAD",
    today: date | None = None,
) -> list[Problem]:
    """Check a whole Stack: every version folder, then its Question Bank."""
    bank, bank_problems = read_bank(stack_dir)
    problems: list[Problem] = []
    for folder in _version_dirs(stack_dir):
        problems += _check_version(folder, bank, links)
    return problems + bank_problems + _check_bank(stack_dir, bank, baseline, today or utc_today())


def load_checked_folder(path: Path) -> ContentFolder:
    """The version folder with its Stack's Question Bank, if they pass the check (links aside,
    and with no git baseline: the importer loads what was checked at commit). Raises
    `ContentError` otherwise."""
    bank, problems = read_bank(path.parent)
    folder, folder_problems = read_folder(path, (bank, []))
    problems += folder_problems
    if folder is not None:
        problems += _check_legacy_folder(path) + _check_parsed(folder, links=False)
        problems += _check_bank(path.parent, bank, None, utc_today())
    errors = [p for p in problems if p.level == "error"]
    if errors or folder is None:
        raise ContentError(errors)
    return folder


def _check_version(path: Path, bank: Bank, links: bool) -> list[Problem]:
    folder, problems = read_folder(path, (bank, []))
    problems += _check_legacy_folder(path)
    if folder is None:
        return problems  # the rules below assume a well-formed syllabus
    return problems + _check_parsed(folder, links=links)


def _check_legacy_folder(path: Path) -> list[Problem]:
    legacy = path / LEGACY_QUESTIONS_DIR
    if not legacy.is_dir():
        return []
    return [
        Problem(
            "error",
            str(legacy),
            "(folder)",
            "Question Banks no longer live in version folders: a Stack has one Question Bank, "
            f"in content/<stack-id>/{QUESTION_BANK_DIR}/ (see content-migrate-bank)",
        )
    ]


def _check_parsed(folder: ContentFolder, links: bool) -> list[Problem]:
    syllabus_file = str(folder.path / SYLLABUS_FILE)
    problems = (
        _check_permanent_ids(folder)
        + _check_syllabus(folder, syllabus_file)
        + _check_across_versions(folder)
    )
    if links:
        problems += _check_links(folder.syllabus.materials, syllabus_file)
    return problems


def _id_items(folder: ContentFolder) -> list[tuple[str, str, Path]]:
    """(kind, permanent id, file) for every item of the Syllabus with a permanent ID."""
    s = folder.syllabus
    syllabus_file = folder.path / SYLLABUS_FILE
    items: list[tuple[str, str, Path]] = [("Stack", s.stack.id, syllabus_file)]
    items += [("Material", m.id, syllabus_file) for m in s.materials]
    for week in s.weeks:
        items.append(("Week", week.id, syllabus_file))
        items += [("Lesson", x.id, syllabus_file) for x in week.lessons]
        items += [("Milestone", x.id, syllabus_file) for x in week.milestones]
    return items


def _bank_id_items(bank: Bank) -> list[tuple[str, str, Path]]:
    """(kind, permanent id, file) for every Concept and Question of the Question Bank."""
    items = [("Concept", c.id, path) for path, c in bank.concepts()]
    return items + [("Question", q.id, path) for path, q in bank.questions()]


def _check_permanent_ids(folder: ContentFolder) -> list[Problem]:
    """No two items of any kind share a permanent ID within a Syllabus version: Learner data
    refers to content by (stack id, permanent id) alone. (The Question Bank's IDs are checked
    with the bank, against the newest version.)"""
    return _duplicate_ids(_id_items(folder), folder.path)


def _duplicate_ids(items: list[tuple[str, str, Path]], relative_to: Path) -> list[Problem]:
    """Each reuse of an ID among `items`, reported in the file that reuses it, naming the kind
    and file (relative to `relative_to`) that had it first."""
    problems: list[Problem] = []
    first: dict[str, tuple[str, Path]] = {}
    for kind, item_id, path in items:
        if item_id not in first:
            first[item_id] = (kind, path)
            continue
        first_kind, first_path = first[item_id]
        where = first_path.relative_to(relative_to).as_posix()
        problems.append(
            Problem(
                "error",
                str(path),
                item_id,
                f"duplicate permanent id ({kind}): already used by a {first_kind} in {where}",
            )
        )
    return problems


def _check_syllabus(folder: ContentFolder, file: str) -> list[Problem]:
    s = folder.syllabus
    problems: list[Problem] = []
    # content/<stack-id>/<version>/: so no two Stack folders can claim the same Stack id.
    where = folder.path.resolve()
    if s.version != where.name:
        problems.append(
            Problem(
                "error", file, s.version, f"version doesn't match its folder name '{where.name}'"
            )
        )
    if s.stack.id != where.parent.name:
        problems.append(
            Problem(
                "error",
                file,
                s.stack.id,
                f"Stack id doesn't match its folder name '{where.parent.name}'; "
                "a Stack's versions live in content/<stack-id>/<version>/",
            )
        )

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


def _check_bank(stack_dir: Path, bank: Bank, baseline: str | None, today: date) -> list[Problem]:
    """The Question Bank's own rules, against the Stack's newest Syllabus version, then the rules
    against the git `baseline`."""
    versions = [f for f in (read_folder(p, (bank, []))[0] for p in stack_versions(stack_dir)) if f]
    if not bank.files and not bank.path.is_dir():
        return []  # a Stack with no Question Bank yet: each Lesson's warning says so below
    newest = versions[-1] if versions else None
    return (
        _check_bank_ids(stack_dir, bank, versions)
        + _check_bank_items(bank, newest)
        + _check_against_baseline(stack_dir, bank, baseline, today)
    )


def _check_bank_ids(stack_dir: Path, bank: Bank, versions: list[ContentFolder]) -> list[Problem]:
    """Concept and Question IDs are unique within the bank and never shared with an item of the
    newest Syllabus. Nor do they reuse an ID an earlier version gave another kind of item."""
    newest = _id_items(versions[-1]) if versions else []
    syllabus_file = str(versions[-1].path / SYLLABUS_FILE) if versions else None
    problems = [
        p
        for p in _duplicate_ids(newest + _bank_id_items(bank), stack_dir)
        if p.file != syllabus_file  # the version's own check reports those
    ]
    in_newest = {item_id for _, item_id, _ in newest}
    first_seen: dict[str, tuple[str, str]] = {}  # id -> (kind, version)
    for old in versions:
        for kind, item_id, _ in _id_items(old):
            first_seen.setdefault(item_id, (kind, old.syllabus.version))
    for kind, item_id, path in _bank_id_items(bank):
        seen = first_seen.get(item_id)
        if seen is not None and seen[0] != kind and item_id not in in_newest:
            problems.append(
                Problem(
                    "error",
                    str(path),
                    item_id,
                    f"permanent id reused: it was a {seen[0]} in {seen[1]}, and a permanent id "
                    "never names a different kind of item, even after it is removed",
                )
            )
    return problems


def _check_bank_items(bank: Bank, newest: ContentFolder | None) -> list[Problem]:
    """References that must resolve, Concepts with a sibling for every Retake, and enough
    Questions in each Lesson for a Lesson Quiz. Retired Questions are never drawn, so they don't
    count toward any minimum, and their Lesson tags and Materials may point at what is gone."""
    problems: list[Problem] = []
    lessons = newest.lessons() if newest is not None else []
    lesson_ids = {lesson.id for lesson in lessons}
    material_ids = {m.id for m in newest.syllabus.materials} if newest is not None else set()
    version = newest.syllabus.version if newest is not None else "no Syllabus version"
    concept_files = {c.id: path for path, c in bank.concepts()}
    question_ids = {q.id for _, q in bank.questions()}
    per_concept: Counter[str] = Counter()
    live_per_concept: Counter[str] = Counter()
    per_lesson: defaultdict[str, list[tuple[Path, str]]] = defaultdict(list)

    for path, q in bank.questions():
        file = str(path)
        live = q.retired is None
        per_concept[q.concept] += 1
        if q.concept not in concept_files:
            problems.append(Problem("error", file, q.id, f"unknown concept '{q.concept}'"))
        if isinstance(q, MultipleChoiceQuestion):
            choice_ids = [c.id for c in q.choices]
            if _duplicates(choice_ids):
                problems.append(Problem("error", file, q.id, "duplicate choice ids"))
            if q.answer not in choice_ids:
                problems.append(Problem("error", file, q.id, "answer is not one of the choices"))
        if q.retired is not None:
            replacement = q.retired.replaced_by
            if replacement == q.id:
                problems.append(Problem("error", file, q.id, "a Question can't replace itself"))
            elif replacement is not None and replacement not in question_ids:
                problems.append(
                    Problem(
                        "error",
                        file,
                        q.id,
                        f"retired/replaced_by: '{replacement}' is not a Question in the bank",
                    )
                )
        if not live:
            continue
        live_per_concept[q.concept] += 1
        if newest is None:
            continue  # no Syllabus to resolve against: its own check reports why
        for ref in q.materials:
            if ref not in material_ids:
                problems.append(
                    Problem(
                        "error",
                        file,
                        q.id,
                        f"unknown material '{ref}': a Question's Materials must be in the Stack's "
                        f"newest Syllabus ({version})",
                    )
                )
        if q.lesson is not None:
            if q.lesson in lesson_ids:
                per_lesson[q.lesson].append((path, q.type))
            else:
                problems.append(
                    Problem(
                        "error",
                        file,
                        q.id,
                        f"lesson '{q.lesson}' is not in the Stack's newest Syllabus ({version}); "
                        "re-tag the Question, or retire it",
                    )
                )

    for concept, path in concept_files.items():
        total, live_count = per_concept[concept], live_per_concept[concept]
        if total == 0 or 0 < live_count < MIN_QUESTIONS_PER_CONCEPT:
            problems.append(
                Problem(
                    "error",
                    str(path),
                    concept,
                    f"Concept has {live_count} Question(s) that aren't retired; needs at least "
                    f"{MIN_QUESTIONS_PER_CONCEPT} so a Retake always has a sibling",
                )
            )

    missing: list[str] = []
    for lesson in lessons:
        tagged = per_lesson.get(lesson.id, [])
        if not tagged:
            missing.append(lesson.id)
            continue
        file = str(tagged[0][0])
        if len(tagged) < LESSON_MIN:
            problems.append(
                Problem(
                    "error",
                    file,
                    lesson.id,
                    f"the Lesson has {len(tagged)} Questions that aren't retired; needs at least "
                    f"{LESSON_MIN}",
                )
            )
        types = Counter(t for _, t in tagged)
        mc, written = types["multiple_choice"], types["written"]
        if mc < QUIZ_MULTIPLE_CHOICE or written < QUIZ_WRITTEN:
            problems.append(
                Problem(
                    "error",
                    file,
                    lesson.id,
                    f"a Lesson Quiz needs {QUIZ_MULTIPLE_CHOICE} multiple-choice and "
                    f"{QUIZ_WRITTEN} written Questions; the Lesson has {mc} and {written} "
                    "that aren't retired",
                )
            )
    if missing:
        problems.append(
            Problem(
                "warning",
                str(bank.path),
                f"{len(missing)} lessons",
                f"no Questions yet (first: {', '.join(missing[:3])})",
            )
        )
    return problems


def _check_against_baseline(
    stack_dir: Path, bank: Bank, baseline: str | None, today: date
) -> list[Problem]:
    """The append-only rules (ADR-0004), against the bank as committed at `baseline`."""
    if baseline is None:
        return []
    try:
        committed = read_baseline(stack_dir, baseline)
    except BaselineUnavailable as e:
        return [
            Problem(
                "warning",
                str(bank.path),
                "(baseline)",
                f"no git baseline ({e}): skipped the rules against committed Questions "
                "(never deleted or edited; new Questions' Sources accessed in this run)",
            )
        ]
    except BadBaseline as e:
        return [Problem("error", str(bank.path), "(baseline)", str(e))]

    ref = committed.ref
    problems: list[Problem] = []
    current = {q.id for _, q in bank.questions()}
    for qid, gone in committed.questions.items():
        if qid not in current:
            problems.append(
                Problem(
                    "error",
                    str(stack_dir / gone.file),
                    qid,
                    f"deleted since {ref}: a committed Question is never deleted; retire it "
                    "instead",
                )
            )

    earliest = today - timedelta(days=1)
    committed_on: dict[str, str] = {}  # Concept -> a committed Question testing it
    for question in committed.questions.values():
        committed_on.setdefault(question.concept, question.id)
    for path, q in bank.questions():
        file = str(path)
        old = committed.questions.get(q.id)
        if old is None:
            for i, source in enumerate(q.sources):
                if not earliest <= source.accessed <= today:
                    problems.append(
                        Problem(
                            "error",
                            file,
                            q.id,
                            f"sources/{i}/accessed: {source.accessed} is not in this run; a new "
                            f"Question's Sources are accessed today or yesterday (UTC: "
                            f"{earliest} or {today})",
                        )
                    )
            sibling = committed_on.get(q.concept)
            if sibling is not None:
                problems.append(
                    Problem(
                        "warning",
                        file,
                        q.id,
                        f"tests the Concept '{q.concept}', which {sibling} already tests: a "
                        "repeat is allowed, but make sure it is deliberate",
                    )
                )
            continue
        fields, retired = question_fields(q.model_dump(mode="json"))
        if old.legacy:
            fields.pop("sources", None)  # Questions from before Sources gain them once
        differ = sorted(
            k for k in fields.keys() | old.fields.keys() if fields.get(k) != old.fields.get(k)
        )
        if differ:
            problems.append(
                Problem(
                    "error",
                    file,
                    q.id,
                    f"changed since {ref} ({', '.join(differ)}): a committed Question is never "
                    "edited; retire it (replaced_by a new Question) or change only its Lesson tag",
                )
            )
        if old.retired is not None and retired != old.retired:
            problems.append(
                Problem(
                    "error",
                    file,
                    q.id,
                    f"its retirement changed since {ref}: a retirement is final, and never "
                    "edited or undone",
                )
            )
    return problems


def _check_across_versions(folder: ContentFolder) -> list[Problem]:
    """Rules against the Stack's earlier versions, which sit beside this folder."""
    earlier_paths = earlier_versions(folder.path.resolve())
    earlier = [
        f for f in (read_folder(p, (folder.bank, []))[0] for p in earlier_paths) if f is not None
    ]
    problems = _check_kinds_across_versions(folder, earlier)
    if not earlier_paths:
        return problems + _check_changelog(folder, None)
    if not earlier or earlier[-1].path != earlier_paths[-1]:
        problems.append(
            Problem(
                "warning",
                str(folder.path / CHANGELOG_FILE),
                earlier_paths[-1].name,
                "can't hold the changelog to the version before: that version doesn't pass "
                "the format",
            )
        )
        return problems
    return problems + _check_changelog(folder, earlier[-1])


def _check_kinds_across_versions(
    folder: ContentFolder, earlier: list[ContentFolder]
) -> list[Problem]:
    """A permanent ID keeps its kind for good: Learner data keyed by it outlives the item. So an
    ID that an earlier version used (even one that was removed since) never comes back as a
    different kind of item."""
    first_seen: dict[str, tuple[str, str]] = {}  # id -> (kind, version)
    for old in earlier:
        for kind, item_id, _ in _id_items(old):
            first_seen.setdefault(item_id, (kind, old.syllabus.version))
    problems: list[Problem] = []
    for kind, item_id, path in _id_items(folder):
        seen = first_seen.get(item_id)
        if seen is not None and seen[0] != kind:
            problems.append(
                Problem(
                    "error",
                    str(path),
                    item_id,
                    f"permanent id reused: it was a {seen[0]} in {seen[1]}, and a permanent id "
                    "never names a different kind of item, even after it is removed",
                )
            )
    return problems


def _check_changelog(folder: ContentFolder, previous: ContentFolder | None) -> list[Problem]:
    """A version that follows another says what changed: every added, changed or removed Lesson
    has an entry, and every entry matches what `content-diff` finds. A first version needs no
    changelog, but one it has is held to the same rules."""
    file = str(folder.path / CHANGELOG_FILE)
    if not folder.has_changelog_file:
        if previous is None:
            return []
        return [
            Problem(
                "error",
                file,
                "(file)",
                f"missing: a version that follows {previous.syllabus.version} must say what "
                "changed, why, and its sources",
            )
        ]
    log = folder.changelog
    if log is None:
        return []  # it breaks the format, which is already reported

    problems: list[Problem] = []
    version = folder.syllabus.version
    if log.version != version:
        problems.append(
            Problem(
                "error",
                file,
                "version",
                f"the changelog is for {log.version}, but this folder is {version}",
            )
        )
    expected = previous.syllabus.version if previous is not None else None
    if log.previous_version != expected:
        before = expected or "none: this is the Stack's first version"
        problems.append(
            Problem(
                "error",
                file,
                "previous_version",
                f"the changelog follows {log.previous_version or 'nothing'}, but the version "
                f"before this one is {before}",
            )
        )

    since = expected or "nothing (this is the first version)"
    actual = {(c.kind, c.id): c.change for c in diff_contents(previous, folder)}
    listed: dict[tuple[ItemKind, str], str] = {}
    for entry in log.changes:
        if (entry.kind, entry.id) in listed:
            problems.append(
                Problem("error", file, entry.id, "listed more than once in the changelog")
            )
        listed.setdefault((entry.kind, entry.id), entry.change)
    for (kind, item_id), change in actual.items():
        if kind is ItemKind.LESSON and (kind, item_id) not in listed:
            problems.append(
                Problem(
                    "error",
                    file,
                    item_id,
                    f"the Lesson was {change} since {since}, but the changelog doesn't list it",
                )
            )
    for (kind, item_id), claimed in listed.items():
        was = actual.get((kind, item_id))
        if was == claimed:
            continue
        claim = f"the changelog says the {kind.label} was {claimed}"
        if kind in (ItemKind.CONCEPT, ItemKind.QUESTION):
            message = (
                f"{claim}, but the changelog covers the Syllabus only: the Question Bank is the "
                "Stack's, and each Question carries its own Sources and retirement reason"
            )
        elif was is None:
            message = f"{claim}, but it didn't change since {since}"
        else:
            message = f"{claim}, but since {since} it was {was}"
        problems.append(Problem("error", file, item_id, message))
    return problems


# 401/403/429 usually mean the site blocks automated requests, not that the link is dead.
_BLOCKED = {401, 403, 429}


def _check_links(materials: list[Material], file: str) -> list[Problem]:
    headers = {"User-Agent": "Mozilla/5.0 (content-check; +learning-app)"}

    def get(url: str) -> httpx.Response:
        # A network failure is tried once more, so one flaky moment doesn't fail the check.
        with httpx.Client(follow_redirects=True, timeout=20, headers=headers) as client:
            try:
                return client.get(url)
            except httpx.TransportError:
                return client.get(url)

    def probe(m: Material) -> Problem | None:
        try:
            r = get(m.url)
        except httpx.HTTPError as e:
            return Problem("error", file, m.id, f"link doesn't load: {type(e).__name__} ({m.url})")
        if r.status_code in _BLOCKED:
            return Problem("warning", file, m.id, f"site refused the check (HTTP {r.status_code})")
        if r.status_code >= 400:
            return Problem(
                "error", file, m.id, f"link doesn't load: HTTP {r.status_code} ({m.url})"
            )
        return None

    with ThreadPoolExecutor(max_workers=16) as pool:
        return [p for p in pool.map(probe, materials) if p]


def version_folders(paths: list[Path]) -> list[Path]:
    """Each path as a Stack version folder, or every <stack>/v* folder under a Stack folder or a
    content root (each Stack's versions oldest first)."""
    found: list[Path] = []
    for path in paths:
        if (path / SYLLABUS_FILE).exists():
            found.append(path)
        elif _is_stack_dir(path):
            found += _version_dirs(path)
        else:
            found += sorted((p for p in path.glob("*/v*") if p.is_dir()), key=_folder_order)
    return found


def stack_folders(paths: list[Path]) -> list[Path]:
    """The Stack folders the paths name: a version folder names its Stack; a content root names
    every Stack under it. Each Stack once, in the order found."""
    found: list[Path] = []
    for path in paths:
        if (path / SYLLABUS_FILE).exists():
            stacks = [path.parent]
        elif _is_stack_dir(path):
            stacks = [path]
        else:
            stacks = sorted(p for p in path.iterdir() if _is_stack_dir(p)) if path.is_dir() else []
        found += [s for s in stacks if s.resolve() not in {f.resolve() for f in found}]
    return found


def _is_stack_dir(path: Path) -> bool:
    return path.is_dir() and (
        (path / QUESTION_BANK_DIR).is_dir() or any(p.is_dir() for p in path.glob("v*"))
    )


def _version_dirs(stack_dir: Path) -> list[Path]:
    return sorted((p for p in stack_dir.glob("v*") if p.is_dir()), key=_folder_order)


def _folder_order(folder: Path) -> tuple[str, bool, VersionKey, str]:
    """By Stack, then by version; a folder whose name isn't a version goes last."""
    if is_version(folder.name):
        return folder.parent.name, False, version_key(folder.name), ""
    return folder.parent.name, True, (date.min, 0), folder.name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Stack content before commit.")
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument("--links", action="store_true", help="also check every Material link loads")
    parser.add_argument(
        "--baseline",
        default="HEAD",
        help="the git ref the Question Bank is held to (default HEAD; CI passes the PR base)",
    )
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=None,
        help="the UTC date of this run, YYYY-MM-DD (default: today)",
    )
    args = parser.parse_args(argv)

    stacks = stack_folders(args.folders)
    if not stacks:
        print("no Stack folders found")
        return 1

    errors = 0
    for stack in stacks:
        problems = check_stack(stack, links=args.links, baseline=args.baseline, today=args.today)
        for p in problems:
            print(p)
        n = sum(p.level == "error" for p in problems)
        errors += n
        print(f"{stack}: {'OK' if n == 0 else f'{n} error(s)'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
