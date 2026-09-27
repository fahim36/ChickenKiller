"""`content-new-version`: the starting point of a Syllabus Update is a copy of the current version,
so everything the update doesn't touch keeps its permanent ID by construction."""

import json
from datetime import date
from pathlib import Path

import pytest

from app.content import new_version as cli
from app.content.new_version import new_version
from tests.conftest import ContentFactory, make_changelog

TODAY = date(2026, 3, 1)


def test_copies_the_newest_version_under_todays_version(make_content: ContentFactory) -> None:
    old = make_content()  # <tmp>/mini-stack/v2026-01-01
    content = old.parent.parent

    new = new_version(content, "mini-stack", today=TODAY)

    assert new == content / "mini-stack" / "v2026-03-01"
    old_text = (old / "syllabus.json").read_text(encoding="utf-8")
    assert (new / "syllabus.json").read_text(encoding="utf-8") == old_text.replace(
        '"version": "v2026-01-01"', '"version": "v2026-03-01"'
    )
    assert not (new / "question-bank").exists()  # the Question Bank is the Stack's, not copied
    assert (content / "mini-stack" / "question-bank" / "w01-l01.json").is_file()
    assert json.loads((old / "syllabus.json").read_text(encoding="utf-8"))["version"] == (
        "v2026-01-01"
    )


def test_a_second_version_on_the_same_day_is_numbered(make_content: ContentFactory) -> None:
    content = make_content().parent.parent

    first = new_version(content, "mini-stack", today=date(2026, 1, 1))
    second = new_version(content, "mini-stack", today=date(2026, 1, 1))

    assert (first.name, second.name) == ("v2026-01-01.1", "v2026-01-01.2")
    assert json.loads((second / "syllabus.json").read_text(encoding="utf-8"))["version"] == (
        "v2026-01-01.2"
    )


def test_the_new_version_starts_its_own_changelog(make_content: ContentFactory) -> None:
    old = make_content(changelog=make_changelog("v2026-01-01", None))
    new = new_version(old.parent.parent, "mini-stack", today=TODAY)

    assert json.loads((new / "changelog.json").read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "version": "v2026-03-01",
        "previous_version": "v2026-01-01",
        "summary": "",
        "changes": [],
    }


def test_a_new_stack_gets_an_empty_first_version(tmp_path: Path) -> None:
    new = new_version(tmp_path, "brand-new-stack", today=TODAY)

    assert new == tmp_path / "brand-new-stack" / "v2026-03-01"
    assert (new.parent / "question-bank").is_dir()
    assert not (new / "syllabus.json").exists()
    assert (
        json.loads((new / "changelog.json").read_text(encoding="utf-8"))["previous_version"] is None
    )


def test_an_existing_version_is_never_overwritten(make_content: ContentFactory) -> None:
    content = make_content().parent.parent

    with pytest.raises(FileExistsError):
        new_version(content, "mini-stack", today=TODAY, version="v2026-01-01")


def test_a_new_version_always_sorts_last(make_content: ContentFactory) -> None:
    content = make_content().parent.parent

    with pytest.raises(ValueError, match="would sort before the newest version, v2026-01-01"):
        new_version(content, "mini-stack", today=TODAY, version="v2025-12-31")


def test_cli_prints_the_new_folder(
    make_content: ContentFactory, capsys: pytest.CaptureFixture[str]
) -> None:
    content = make_content().parent.parent

    code = cli.main(["mini-stack", "--content", str(content), "--version", "v2026-02-01"])

    assert code == 0
    assert (content / "mini-stack" / "v2026-02-01" / "syllabus.json").exists()
    assert str(content / "mini-stack" / "v2026-02-01") in capsys.readouterr().out
