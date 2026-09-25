"""`content-diff`: what a new Syllabus version added, changed and removed, by permanent ID."""

import json
from datetime import date
from typing import Any

import pytest

from app.content import diff as cli
from app.content.diff import Change, diff_versions
from app.content.new_version import new_version
from tests.conftest import ContentFactory, as_version, make_bank


def as_tuples(changes: list[Change]) -> list[tuple[str, str, str, tuple[str, ...]]]:
    return [(c.change, c.kind.label, c.id, c.fields) for c in changes]


def test_an_unchanged_copy_has_an_empty_diff(make_content: ContentFactory) -> None:
    old = make_content()
    new = new_version(old.parent.parent, "mini-stack", today=date(2026, 2, 1))

    assert diff_versions(old, new) == []


def test_lists_added_changed_and_removed_items_by_kind(make_content: ContentFactory) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        week = syllabus["weeks"][0]
        week["lessons"][0]["title"] = "First lesson, revised"
        week["lessons"][0]["minutes"] = 90
        week["lessons"].append(
            {
                "id": "w01-l03",
                "title": "Third lesson",
                "topics": ["Topic D"],
                "exercise": None,
                "minutes": 30,
                "materials": [],
            }
        )
        syllabus["materials"][1]["url"] = "https://example.com/video-v2"
        del bank["questions"][1]  # w01-l01-q02

    old = make_content()
    new = make_content(as_version("v2026-02-01", edit))

    assert as_tuples(diff_versions(old, new)) == [
        ("changed", "Week", "w01", ("lessons",)),
        ("added", "Lesson", "w01-l03", ()),
        ("changed", "Lesson", "w01-l01", ("title", "minutes", "question_bank")),
        ("changed", "Material", "mat-video", ("url",)),
        ("removed", "Question", "w01-l01-q02", ()),
    ]


def test_a_new_question_bank_changes_its_lesson(make_content: ContentFactory) -> None:
    old = make_content()
    new = make_content(
        as_version("v2026-02-01"), extra_banks={"w01-l02": make_bank("w01-l02", "second")}
    )

    changes = as_tuples(diff_versions(old, new))

    assert changes[0] == ("changed", "Lesson", "w01-l02", ("question_bank",))
    assert [c[:3] for c in changes[1:]] == [
        ("added", "Concept", "second-a"),
        ("added", "Concept", "second-b"),
        ("added", "Concept", "second-c"),
        ("added", "Concept", "second-d"),
        *[("added", "Question", f"w01-l02-q{n:02}") for n in range(1, 9)],
    ]


def test_a_first_version_adds_everything(make_content: ContentFactory) -> None:
    changes = diff_versions(None, make_content())

    assert {c.change for c in changes} == {"added"}
    assert [c.id for c in changes if c.kind.label == "Lesson"] == ["w01-l01", "w01-l02"]
    assert len(changes) == 1 + 1 + 2 + 1 + 2 + 4 + 8  # Stack, Week, Lessons, ..., Questions


def test_cli_prints_one_line_per_change(
    make_content: ContentFactory, capsys: pytest.CaptureFixture[str]
) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["weeks"][0]["lessons"][1]["title"] = "Renamed"

    old, new = make_content(), make_content(as_version("v2026-02-01", edit))

    assert cli.main([str(old), str(new)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[-2:] == [
        "changed  Lesson     w01-l02  (title)",
        "0 added, 1 changed, 0 removed",
    ]


def test_cli_compares_with_the_previous_version_when_given_one_folder(
    make_content: ContentFactory, capsys: pytest.CaptureFixture[str]
) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["weeks"][0]["lessons"][1]["title"] = "Renamed"

    make_content()
    new = make_content(as_version("v2026-02-01", edit))

    assert cli.main([str(new), "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "old": "v2026-01-01",
        "new": "v2026-02-01",
        "changes": [{"kind": "lesson", "id": "w01-l02", "change": "changed", "fields": ["title"]}],
    }
