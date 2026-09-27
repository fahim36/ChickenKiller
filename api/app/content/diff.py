"""What one Syllabus version added, changed and removed compared with another, by permanent ID,
and what the Stack's Question Bank added, retired and re-tagged since it was committed.

    content-diff <old-folder> <new-folder> [--json] [--baseline REF]
    content-diff <new-folder> [--json] [--baseline REF]   (compares with the version before it)

An item is matched across versions by its permanent ID alone; the `version` string itself is not
a change. So a new version that was copied and left alone has an empty diff.

- A **Lesson** is changed when its own fields change (title, topics, exercise, minutes,
  materials), or when it moves to another Week. Its place within the Week is not a change.
- A **Week** is changed when its own fields change, or its list of Lessons or Milestones does.
- The Question Bank is the Stack's, not a version's (ADR-0004), so Concepts and Questions are not
  in the version diff. They are listed separately (`bank_changes`), against the bank as committed
  at the git `--baseline` (default `HEAD`, which is what a Syllabus Update in progress needs):
  each Question added, retired or re-tagged to another Lesson, by permanent ID. That list is for
  review; the changelog doesn't repeat it, since each Question carries its own Sources and each
  retirement its reason.

The Syllabus Update writes its changelog from this list, and the content check holds the changelog
to it (`app.content.check`). The importer stores each Lesson's `lesson_fingerprints`, so the app
can tell a Learner's Completed Lesson changed since the version they completed it in (#13): the
same fields, plus the Questions tagged to the Lesson when the version was imported.
"""

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from app.content.baseline import BadBaseline, BaselineUnavailable, read_baseline
from app.content.format import ItemKind
from app.content.loader import ContentFolder, read_bank, read_folder
from app.content.versions import earlier_versions

ChangeType = Literal["added", "changed", "removed"]
_CHANGE_ORDER: tuple[ChangeType, ...] = ("added", "changed", "removed")
_KIND_ORDER = list(ItemKind)


@dataclass(frozen=True)
class Change:
    kind: ItemKind
    id: str
    change: ChangeType
    fields: tuple[str, ...] = ()  # for "changed": which fields differ

    def __str__(self) -> str:
        fields = f"  ({', '.join(self.fields)})" if self.fields else ""
        return f"{self.change:8} {self.kind.label:10} {self.id}{fields}"

    def as_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "id": self.id,
            "change": self.change,
            "fields": list(self.fields),
        }


@dataclass(frozen=True)
class Item:
    kind: ItemKind
    fields: dict[str, Any]


def content_items(folder: ContentFolder) -> dict[str, Item]:
    """Every item of the Syllabus with a permanent ID, in the order the file lists them."""
    s = folder.syllabus
    items: dict[str, Item] = {
        s.stack.id: Item(ItemKind.STACK, s.stack.model_dump(mode="json", exclude={"id"}))
    }
    for week in s.weeks:
        fields = week.model_dump(mode="json", exclude={"id", "lessons", "milestones"})
        fields["lessons"] = [x.id for x in week.lessons]
        fields["milestones"] = [x.id for x in week.milestones]
        items[week.id] = Item(ItemKind.WEEK, fields)
        for lesson in week.lessons:
            fields = lesson.model_dump(mode="json", exclude={"id"})
            fields["week"] = week.id
            items[lesson.id] = Item(ItemKind.LESSON, fields)
        for milestone in week.milestones:
            fields = milestone.model_dump(mode="json", exclude={"id"})
            fields["week"] = week.id
            items[milestone.id] = Item(ItemKind.MILESTONE, fields)
    for material in s.materials:
        items[material.id] = Item(
            ItemKind.MATERIAL, material.model_dump(mode="json", exclude={"id"})
        )
    return items


def lesson_questions(folder: ContentFolder) -> dict[str, list[str]]:
    """The Questions (permanent IDs, bank order) tagged to each Lesson of the version, leaving
    out Retired Questions. Every Lesson is listed, with none if it has none."""
    tagged: dict[str, list[str]] = {lesson.id: [] for lesson in folder.lessons()}
    for question in folder.bank.live_questions():
        if question.lesson in tagged:
            tagged[question.lesson].append(question.id)
    return tagged


def lesson_fingerprints(folder: ContentFolder) -> dict[str, str]:
    """A hash of each Lesson's content, by permanent ID: its fields as `diff_contents` compares
    them, plus the Questions tagged to it now (`lesson_questions`). The importer stores it with
    each version, so two versions' fingerprints of a Lesson are equal exactly when the diff
    wouldn't list it as changed and the version brought it no Question added, retired or
    re-tagged."""
    questions = lesson_questions(folder)
    return {
        item_id: hashlib.sha256(
            json.dumps(
                {**item.fields, "questions": sorted(questions[item_id])}, sort_keys=True
            ).encode()
        ).hexdigest()
        for item_id, item in content_items(folder).items()
        if item.kind == ItemKind.LESSON
    }


def diff_contents(old: ContentFolder | None, new: ContentFolder) -> list[Change]:
    """The changes from `old` to `new`; with no `old` (a first version), everything is added.
    Listed by kind (Stack, Week, Lesson, ...), then added, changed, removed."""
    before = content_items(old) if old is not None else {}
    after = content_items(new)
    changes: list[Change] = []
    for item_id, item in after.items():
        was = before.get(item_id)
        if was is None or was.kind != item.kind:
            changes.append(Change(item.kind, item_id, "added"))
        elif was.fields != item.fields:
            differ = tuple(k for k in item.fields if was.fields.get(k) != item.fields[k])
            changes.append(Change(item.kind, item_id, "changed", differ))
    for item_id, item in before.items():
        now = after.get(item_id)
        if now is None or now.kind != item.kind:
            changes.append(Change(item.kind, item_id, "removed"))
    return sorted(changes, key=lambda c: (_KIND_ORDER.index(c.kind), _CHANGE_ORDER.index(c.change)))


BankChangeType = Literal["added", "retired", "re-tagged"]
_BANK_ORDER: tuple[BankChangeType, ...] = ("added", "retired", "re-tagged")


@dataclass(frozen=True)
class BankChange:
    """One Question the bank added, retired or re-tagged since the baseline."""

    id: str
    change: BankChangeType
    lesson: str | None  # its Lesson tag now
    was: str | None = None  # for "re-tagged": the Lesson it was tagged to
    replaced_by: str | None = None  # for "retired"

    def __str__(self) -> str:
        if self.change == "re-tagged":
            note = f"{self.was or 'no Lesson'} -> {self.lesson or 'no Lesson'}"
        elif self.change == "retired":
            note = f"replaced by {self.replaced_by}" if self.replaced_by else "no replacement"
        else:
            note = self.lesson or "no Lesson"
        return f"{self.change:9} Question   {self.id}  ({note})"

    def as_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "change": self.change,
            "lesson": self.lesson,
            "was": self.was,
            "replaced_by": self.replaced_by,
        }


def bank_changes(stack_dir: Path, baseline: str = "HEAD") -> list[BankChange]:
    """The Questions added, retired or re-tagged in the Stack's Question Bank since `baseline`,
    added first, then retired, then re-tagged, each in bank order. A Question both retired and
    re-tagged is listed as retired. Raises `BaselineUnavailable` or `BadBaseline` (from
    `app.content.baseline`), and `ValueError` if the bank can't be read."""
    bank, problems = read_bank(stack_dir)
    if errors := [p for p in problems if p.level == "error"]:
        raise ValueError(f"can't read {bank.path}: " + "; ".join(str(p) for p in errors))
    committed = read_baseline(stack_dir, baseline).questions
    changes: list[BankChange] = []
    for _, q in bank.questions():
        old = committed.get(q.id)
        if old is None:
            changes.append(BankChange(q.id, "added", q.lesson))
        elif q.retired is not None and old.retired is None:
            changes.append(BankChange(q.id, "retired", q.lesson, replaced_by=q.retired.replaced_by))
        elif q.lesson != old.lesson:
            changes.append(BankChange(q.id, "re-tagged", q.lesson, was=old.lesson))
    return sorted(changes, key=lambda c: _BANK_ORDER.index(c.change))


def diff_versions(old: Path | None, new: Path) -> list[Change]:
    """`diff_contents` for two version folders. Raises `ValueError` if either can't be read."""
    return diff_contents(_read(old) if old is not None else None, _read(new))


def _read(path: Path) -> ContentFolder:
    folder, problems = read_folder(path)
    if folder is None:
        raise ValueError(f"can't read {path}: " + "; ".join(str(p) for p in problems))
    return folder


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="List what a Syllabus version added, changed and removed, by permanent ID."
    )
    parser.add_argument("folders", nargs="+", type=Path, metavar="folder", help="[old] new")
    parser.add_argument("--json", action="store_true", help="print the changes as JSON")
    parser.add_argument(
        "--baseline",
        default="HEAD",
        help="the git ref the Question Bank is compared with (default HEAD)",
    )
    args = parser.parse_args(argv)
    if len(args.folders) > 2:
        parser.error("give at most two folders: [old] new")
    new: Path = args.folders[-1]
    old: Path | None
    if len(args.folders) == 2:
        old = args.folders[0]
    else:
        earlier = earlier_versions(new)
        old = earlier[-1] if earlier else None

    try:
        changes = diff_versions(old, new)
    except ValueError as e:
        print(f"ERROR   {e}")
        return 1

    bank: list[BankChange] | None
    try:
        bank = bank_changes(new.parent, args.baseline)
        bank_note = None
    except (BaselineUnavailable, BadBaseline, ValueError) as e:
        bank, bank_note = None, str(e)

    old_name = old.name if old is not None else None
    if args.json:
        doc = {
            "old": old_name,
            "new": new.name,
            "changes": [c.as_json() for c in changes],
            "bank": {
                "baseline": args.baseline,
                "changes": [c.as_json() for c in bank] if bank is not None else None,
                "error": bank_note,
            },
        }
        print(json.dumps(doc, indent=2))
        return 0
    print(f"{old if old is not None else '(nothing: first version)'} -> {new}")
    for change in changes:
        print(change)
    counts = {kind: sum(c.change == kind for c in changes) for kind in _CHANGE_ORDER}
    print(", ".join(f"{n} {kind}" for kind, n in counts.items()))
    print()
    print(f"Question Bank since {args.baseline}:")
    if bank is None:
        print(f"  can't compare: {bank_note}")
        return 0
    for bank_change in bank:
        print(bank_change)
    bank_counts = {kind: sum(c.change == kind for c in bank) for kind in _BANK_ORDER}
    print(", ".join(f"{n} {kind}" for kind, n in bank_counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
