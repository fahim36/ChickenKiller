"""The content check across versions: a version that follows another has a changelog that
matches what changed, and a permanent ID never comes back as a different kind of item."""

from pathlib import Path
from typing import Any

from app.content.check import Problem, check_folder
from tests.conftest import (
    ContentFactory,
    as_version,
    changelog_entry,
    make_bank,
    make_changelog,
)

V1, V2, V3 = "v2026-01-01", "v2026-01-01.1", "v2026-02-01"


def error_problems(folder: Path) -> list[Problem]:
    return [p for p in check_folder(folder) if p.level == "error"]


def errors(folder: Path) -> list[str]:
    return [f"{p.item}: {p.message}" for p in error_problems(folder)]


def retitle_first_lesson(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    syllabus["weeks"][0]["lessons"][0]["title"] = "First lesson, revised"


def test_a_version_after_another_needs_a_changelog(make_content: ContentFactory) -> None:
    make_content()
    new = make_content(as_version(V2, retitle_first_lesson))

    [problem] = error_problems(new)
    assert Path(problem.file) == new / "changelog.json"
    assert problem.message == (
        f"missing: a version that follows {V1} must say what changed, why, and its sources"
    )


def test_a_changelog_that_lists_every_lesson_change_passes(make_content: ContentFactory) -> None:
    make_content()
    log = make_changelog(V2, V1, changelog_entry("lesson", "w01-l01", "changed"))

    assert errors(make_content(as_version(V2, retitle_first_lesson), changelog=log)) == []


def test_every_added_changed_and_removed_lesson_must_be_listed(
    make_content: ContentFactory,
) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        lessons = syllabus["weeks"][0]["lessons"]
        retitle_first_lesson(syllabus, bank)
        lessons[1] = {**lessons[1], "id": "w01-l03", "title": "A new lesson"}  # w01-l02 removed

    make_content()
    new = make_content(as_version(V2, edit), changelog=make_changelog(V2, V1))

    problems = error_problems(new)
    assert {Path(p.file) for p in problems} == {new / "changelog.json"}
    assert [f"{p.item}: {p.message}" for p in problems] == [
        f"w01-l03: the Lesson was added since {V1}, but the changelog doesn't list it",
        f"w01-l01: the Lesson was changed since {V1}, but the changelog doesn't list it",
        f"w01-l02: the Lesson was removed since {V1}, but the changelog doesn't list it",
    ]


def test_an_entry_must_match_what_actually_changed(make_content: ContentFactory) -> None:
    log = make_changelog(
        V2,
        V1,
        changelog_entry("lesson", "w01-l01", "added"),  # it was changed
        changelog_entry("lesson", "w01-l02", "changed"),  # it didn't change
        changelog_entry("material", "mat-docs", "removed"),  # it is still there
    )
    make_content()
    new = make_content(as_version(V2, retitle_first_lesson), changelog=log)

    assert errors(new) == [
        f"w01-l01: the changelog says the Lesson was added, but since {V1} it was changed",
        f"w01-l02: the changelog says the Lesson was changed, but it didn't change since {V1}",
        f"mat-docs: the changelog says the Material was removed, but it didn't change since {V1}",
    ]


def test_other_kinds_of_change_may_be_listed_too(make_content: ContentFactory) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["materials"][0]["url"] = "https://example.com/docs/v2"

    log = make_changelog(V2, V1, changelog_entry("material", "mat-docs", "changed"))
    make_content()

    assert errors(make_content(as_version(V2, edit), changelog=log)) == []


def test_every_entry_needs_an_https_source(make_content: ContentFactory) -> None:
    no_source = {**changelog_entry("lesson", "w01-l01", "changed"), "sources": []}
    make_content()
    new = make_content(
        as_version(V2, retitle_first_lesson), changelog=make_changelog(V2, V1, no_source)
    )

    [problem] = error_problems(new)
    assert (problem.item, problem.message) == (
        "w01-l01",
        "changes/0/sources: List should have at least 1 item after validation, not 0",
    )


def test_the_changelog_names_this_version_and_the_one_before(
    make_content: ContentFactory,
) -> None:
    make_content()
    log = make_changelog(V3, "v2025-12-31", changelog_entry("lesson", "w01-l01", "changed"))

    assert errors(make_content(as_version(V2, retitle_first_lesson), changelog=log)) == [
        f"version: the changelog is for {V3}, but this folder is {V2}",
        f"previous_version: the changelog follows v2025-12-31, but the version before this one "
        f"is {V1}",
    ]


def test_a_first_version_needs_no_changelog_but_a_given_one_is_checked(
    make_content: ContentFactory,
) -> None:
    log = make_changelog(V1, None, changelog_entry("lesson", "w01-l01", "added"))

    assert errors(make_content(changelog=log)) == [
        "w01-l02: the Lesson was added since nothing (this is the first version), "
        "but the changelog doesn't list it"
    ]


def test_a_removed_id_never_comes_back_as_another_kind(make_content: ContentFactory) -> None:
    def remove_second_lesson(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        del syllabus["weeks"][0]["lessons"][1]

    def reuse_it_as_a_concept(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        remove_second_lesson(syllabus, bank)
        bank["concepts"][0]["id"] = "w01-l02"
        for q in bank["questions"]:
            if q["concept"] == "concept-a":
                q["concept"] = "w01-l02"

    make_content()
    make_content(
        as_version(V2, remove_second_lesson),
        changelog=make_changelog(V2, V1, changelog_entry("lesson", "w01-l02", "removed")),
    )
    new = make_content(as_version(V3, reuse_it_as_a_concept), changelog=make_changelog(V3, V2))

    [problem] = error_problems(new)
    assert Path(problem.file) == new.parent / "question-bank" / "w01-l01.json"
    assert (problem.item, problem.message) == (
        "w01-l02",
        f"permanent id reused: it was a Lesson in {V1}, and a permanent id never names a "
        "different kind of item, even after it is removed",
    )


def test_the_changelog_covers_the_syllabus_only(make_content: ContentFactory) -> None:
    """New Questions change no Lesson in the diff, and a Question entry is refused: the Question
    Bank is the Stack's, and each Question carries its own Sources."""
    make_content()
    log = make_changelog(
        V2,
        V1,
        changelog_entry("lesson", "w01-l02", "changed"),
        changelog_entry("question", "w01-l02-q01", "added"),
    )
    new = make_content(
        as_version(V2), extra_banks={"w01-l02": make_bank("w01-l02", "second")}, changelog=log
    )

    assert errors(new) == [
        f"w01-l02: the changelog says the Lesson was changed, but it didn't change since {V1}",
        "w01-l02-q01: the changelog says the Question was added, but the changelog covers the "
        "Syllabus only: the Question Bank is the Stack's, and each Question carries its own "
        "Sources and retirement reason",
    ]
