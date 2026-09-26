"""`content-migrate-bank`: the one-time move of a Stack's per-version Question Banks into its one
Question Bank, with Sources from sidecar files (#15)."""

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from app.content import migrate_bank as cli
from app.content.check import check_stack
from app.content.migrate_bank import migrate_bank
from tests.conftest import (
    BANK,
    LESSON,
    SYLLABUS,
    changelog_entry,
    make_bank,
    make_changelog,
    source,
)

V1, V2 = "v2026-01-01", "v2026-02-01"
TODAY = date(2026, 2, 2)


def legacy_bank(lesson: str, concept_prefix: str = "concept") -> dict[str, Any]:
    """A Question Bank in the old layout: one per Lesson, no Sources, no Lesson tags."""
    bank = copy.deepcopy(BANK) if lesson == LESSON else make_bank(lesson, concept_prefix)
    for question in bank["questions"]:
        del question["sources"], question["lesson"]
    return {**bank, "schema_version": 1, "lesson_id": lesson}


def write_version(
    stack: Path,
    version: str,
    banks: dict[str, dict[str, Any]],
    changelog: dict[str, Any] | None = None,
) -> None:
    folder = stack / version
    (folder / "questions").mkdir(parents=True)
    syllabus = copy.deepcopy(SYLLABUS) | {"version": version}
    (folder / "syllabus.json").write_text(json.dumps(syllabus), encoding="utf-8")
    for lesson, bank in banks.items():
        (folder / "questions" / f"{lesson}.json").write_text(json.dumps(bank), encoding="utf-8")
    if changelog is not None:
        (folder / "changelog.json").write_text(json.dumps(changelog), encoding="utf-8")


@pytest.fixture
def stack(tmp_path: Path) -> Path:
    """Version 1 has a bank for w01-l01; version 2 adds one for w01-l02 and rewords q01, and its
    changelog lists w01-l02 as changed for gaining a bank."""
    stack = tmp_path / "content" / "mini-stack"
    write_version(stack, V1, {LESSON: legacy_bank(LESSON)})
    newer = legacy_bank(LESSON)
    newer["questions"][0]["prompt"] = "Question 1, as version 2 has it?"
    write_version(
        stack,
        V2,
        {LESSON: newer, "w01-l02": legacy_bank("w01-l02", "second")},
        make_changelog(V2, V1, changelog_entry("lesson", "w01-l02", "changed")),
    )
    return stack


@pytest.fixture
def sources(tmp_path: Path) -> Path:
    """A sidecar per Lesson, giving every Question two Sources; w01-l02-q03 has a problem."""
    folder = tmp_path / "sources"
    folder.mkdir()
    for lesson in (LESSON, "w01-l02"):
        doc = {
            "lesson_id": lesson,
            "questions": {
                f"{lesson}-q{n:02}": {"sources": [source(1), source(2)], "problem": None}
                for n in range(1, 9)
            },
        }
        (folder / f"{lesson}.json").write_text(json.dumps(doc), encoding="utf-8")
    return folder


def bank_file(stack: Path, lesson: str) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(
        (stack / "question-bank" / f"{lesson}.json").read_text(encoding="utf-8")
    )
    return doc


def test_merges_the_banks_into_the_stacks_bank_with_sources(stack: Path, sources: Path) -> None:
    report = migrate_bank(stack, sources, TODAY)

    assert (report.questions, report.files, report.without_sources) == (16, 2, [])
    first = bank_file(stack, LESSON)
    assert first["schema_version"] == 2
    assert [c["id"] for c in first["concepts"]] == [f"concept-{x}" for x in "abcd"]
    q01 = first["questions"][0]
    assert list(q01) == [
        "id",
        "lesson",
        "concept",
        "type",
        "prompt",
        "choices",
        "answer",
        "explanation",
        "materials",
        "sources",
    ]
    assert (q01["lesson"], q01["prompt"]) == (LESSON, "Question 1, as version 2 has it?")
    assert q01["sources"] == [source(1), source(2)]
    assert not (stack / V1 / "questions").exists() and not (stack / V2 / "questions").exists()


def test_the_migrated_stack_passes_the_check(stack: Path, sources: Path) -> None:
    migrate_bank(stack, sources, TODAY)

    assert [p for p in check_stack(stack, baseline=None) if p.level == "error"] == []


def test_changelog_entries_about_a_question_bank_are_dropped(stack: Path, sources: Path) -> None:
    report = migrate_bank(stack, sources, TODAY)

    assert report.dropped_changelog_entries == [f"{V2}: changed lesson w01-l02"]
    log = json.loads((stack / V2 / "changelog.json").read_text(encoding="utf-8"))
    assert (log["summary"], log["changes"]) == ("What changed in this version.", [])


def test_a_problem_retires_the_question(stack: Path, sources: Path) -> None:
    sidecar = json.loads((sources / "w01-l02.json").read_text(encoding="utf-8"))
    sidecar["questions"]["w01-l02-q03"]["problem"] = "The answer is out of date."
    (sources / "w01-l02.json").write_text(json.dumps(sidecar), encoding="utf-8")

    report = migrate_bank(stack, sources, TODAY)

    assert report.retired == {"w01-l02-q03": "The answer is out of date."}
    q03 = bank_file(stack, "w01-l02")["questions"][2]
    assert q03["retired"] == {"reason": "The answer is out of date.", "on": "2026-02-02"}


def test_questions_without_sources_are_reported(stack: Path, sources: Path) -> None:
    (sources / "w01-l02.json").unlink()

    report = migrate_bank(stack, sources, TODAY)

    assert report.without_sources == [f"w01-l02-q{n:02}" for n in range(1, 9)]
    assert bank_file(stack, "w01-l02")["questions"][0]["sources"] == []
    assert any("sources" in p.message for p in check_stack(stack, baseline=None))


def test_a_dry_run_writes_nothing(stack: Path, sources: Path) -> None:
    before = sorted(p.relative_to(stack) for p in stack.rglob("*"))

    report = migrate_bank(stack, sources, TODAY, dry_run=True)

    assert report.questions == 16
    assert sorted(p.relative_to(stack) for p in stack.rglob("*")) == before


def test_a_migrated_stack_is_refused(stack: Path, sources: Path) -> None:
    migrate_bank(stack, sources, TODAY)

    with pytest.raises(FileExistsError, match="already migrated"):
        migrate_bank(stack, sources, TODAY)


def test_cli_prints_the_report(
    stack: Path, sources: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = [str(stack), "--sources", str(sources), "--today", "2026-02-02"]
    assert cli.main([*args, "--dry-run"]) == 0
    assert "16 Questions in 2 Question Bank files" in capsys.readouterr().out
    assert cli.main(args) == 0
    assert cli.main(args) == 1
