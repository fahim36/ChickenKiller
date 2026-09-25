"""What one Syllabus version added, changed and removed compared with another, by permanent ID.

    content-diff <old-folder> <new-folder> [--json]
    content-diff <new-folder> [--json]      (compares with the version before it)

An item is matched across versions by its permanent ID alone; the `version` string itself is not
a change. So a new version that was copied and left alone has an empty diff.

- A **Lesson** is changed when its own fields change (title, topics, exercise, minutes,
  materials), when it moves to another Week, or when anything in its Question Bank changes
  (reported as the field `question_bank`). Its place within the Week is not a change.
- A **Week** is changed when its own fields change, or its list of Lessons or Milestones does.
- **Concepts** and **Questions** are listed too, so a Lesson's change can be traced to them.

The Syllabus Update writes its changelog from this list, and the content check holds the changelog
to it (`app.content.check`). Importing a new version without losing progress (#13) uses it too.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from app.content.format import ItemKind
from app.content.loader import ContentFolder, read_folder
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
    """Every item with a permanent ID, in the order the files list them."""
    s = folder.syllabus
    banks = {bank.lesson_id: bank for bank in folder.banks.values()}
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
            bank = banks.get(lesson.id)
            fields["question_bank"] = (
                None if bank is None else bank.model_dump(mode="json", exclude={"lesson_id"})
            )
            items[lesson.id] = Item(ItemKind.LESSON, fields)
        for milestone in week.milestones:
            fields = milestone.model_dump(mode="json", exclude={"id"})
            fields["week"] = week.id
            items[milestone.id] = Item(ItemKind.MILESTONE, fields)
    for material in s.materials:
        items[material.id] = Item(
            ItemKind.MATERIAL, material.model_dump(mode="json", exclude={"id"})
        )
    for bank in folder.banks.values():
        for concept in bank.concepts:
            fields = concept.model_dump(mode="json", exclude={"id"})
            fields["lesson"] = bank.lesson_id
            items[concept.id] = Item(ItemKind.CONCEPT, fields)
        for question in bank.questions:
            fields = question.model_dump(mode="json", exclude={"id"})
            fields["lesson"] = bank.lesson_id
            items[question.id] = Item(ItemKind.QUESTION, fields)
    return items


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

    old_name = old.name if old is not None else None
    if args.json:
        doc = {"old": old_name, "new": new.name, "changes": [c.as_json() for c in changes]}
        print(json.dumps(doc, indent=2))
        return 0
    print(f"{old if old is not None else '(nothing: first version)'} -> {new}")
    for change in changes:
        print(change)
    counts = {kind: sum(c.change == kind for c in changes) for kind in _CHANGE_ORDER}
    print(", ".join(f"{n} {kind}" for kind, n in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
