"""The content check's Question Bank rules (#15, ADR-0004): every Question has Sources, a Retired
Question has a reason and maybe a replacement, and the bank is append-only against what is
committed in git: never deleted, never edited but for retiring or re-tagging, and a new
Question's Sources are from this run. A new Question on a Concept already tested is a warning."""

import copy
import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from app.content import check
from app.content.check import Problem, check_folder, check_stack
from tests.conftest import (
    BANK,
    LESSON,
    SOURCES_ACCESSED,
    SYLLABUS,
    ContentFactory,
    make_bank,
    mc_question,
    source,
    write_folder,
)

TODAY = date(2026, 1, 2)
"""The day of the test run: Sources accessed on 2026-01-01 or 2026-01-02 are from this run."""


def errors(problems: list[Problem]) -> list[str]:
    return [f"{p.item}: {p.message}" for p in problems if p.level == "error"]


def warnings(problems: list[Problem]) -> list[str]:
    return [f"{p.item}: {p.message}" for p in problems if p.level == "warning"]


# --- Sources and retirement ----------------------------------------------------------------


def test_a_question_with_no_source_is_refused(make_content: ContentFactory) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        bank["questions"][0]["sources"] = []
        del bank["questions"][1]["sources"]

    problems = check_folder(make_content(edit), baseline=None)

    assert errors(problems) == [
        "w01-l01-q01: questions/0/multiple_choice/sources: "
        "List should have at least 1 item after validation, not 0",
        "w01-l01-q02: questions/1/multiple_choice/sources: Field required",
    ]


@pytest.mark.parametrize("missing", ["url", "title", "publisher", "accessed", "claim"])
def test_a_source_missing_a_field_is_refused(make_content: ContentFactory, missing: str) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        del bank["questions"][6]["sources"][0][missing]

    [error] = errors(check_folder(make_content(edit), baseline=None))

    assert error == f"w01-l01-q07: questions/6/written/sources/0/{missing}: Field required"


def test_a_source_needs_an_https_url_and_a_real_date(make_content: ContentFactory) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        bank["questions"][0]["sources"][0]["url"] = "http://example.com"
        bank["questions"][1]["sources"][0]["accessed"] = "26 Sep 2026"

    found = errors(check_folder(make_content(edit), baseline=None))

    assert [e.split(":")[0] for e in found] == ["w01-l01-q01", "w01-l01-q02"]
    assert "sources/0/url" in found[0] and "sources/0/accessed" in found[1]


def retire(question: dict[str, Any], replaced_by: str | None = None) -> None:
    question["retired"] = {"reason": "Out of date.", "on": "2026-01-02"}
    if replaced_by is not None:
        question["retired"]["replaced_by"] = replaced_by


def extra_question(qid: str, concept: str = "concept-a") -> dict[str, Any]:
    return mc_question(qid, concept)


def test_a_retired_question_with_its_replacement_passes(make_content: ContentFactory) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        retire(bank["questions"][0], replaced_by="w01-l01-q09")
        bank["questions"].append(extra_question("w01-l01-q09"))

    assert errors(check_folder(make_content(edit), baseline=None)) == []


def test_a_replacement_that_does_not_exist_is_refused(make_content: ContentFactory) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        retire(bank["questions"][0], replaced_by="w01-l01-q99")
        bank["questions"].append(extra_question("w01-l01-q09"))

    assert errors(check_folder(make_content(edit), baseline=None)) == [
        "w01-l01-q01: retired/replaced_by: 'w01-l01-q99' is not a Question in the bank"
    ]


def test_a_retirement_needs_a_reason(make_content: ContentFactory) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        bank["questions"][0]["retired"] = {"replaced_by": "w01-l01-q02"}

    assert errors(check_folder(make_content(edit), baseline=None)) == [
        "w01-l01-q01: questions/0/multiple_choice/retired/reason: Field required"
    ]


def test_retired_questions_count_toward_no_minimum(make_content: ContentFactory) -> None:
    """Retiring q01 leaves concept-a one sibling, and the Lesson seven Questions."""

    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        retire(bank["questions"][0])

    assert errors(check_folder(make_content(edit), baseline=None)) == [
        "concept-a: Concept has 1 Question(s) that aren't retired; needs at least 2 so a Retake "
        "always has a sibling",
        "w01-l01: the Lesson has 7 Questions that aren't retired; needs at least 8",
    ]


def test_a_concept_whose_questions_are_all_retired_is_fine(make_content: ContentFactory) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        retire(bank["questions"][0])
        retire(bank["questions"][1])
        # The tag of a Retired Question may name a Lesson that is gone.
        bank["questions"][1]["lesson"] = "w00-gone"
        bank["questions"] += [extra_question(f"w01-l01-q{n}", "concept-b") for n in (9, 10)]

    assert errors(check_folder(make_content(edit), baseline=None)) == []


def test_the_bank_has_no_maximum(make_content: ContentFactory) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        bank["questions"] += [extra_question(f"w01-l01-q{n}") for n in range(9, 30)]

    assert errors(check_folder(make_content(edit), baseline=None)) == []


def test_a_question_may_have_no_lesson(make_content: ContentFactory) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        bank["questions"] += [mc_question(f"loose-q{n}", "concept-a", lesson=None) for n in (1, 2)]

    assert errors(check_folder(make_content(edit), baseline=None)) == []


def test_questions_resolve_against_the_newest_syllabus(make_content: ContentFactory) -> None:
    """A Material or Lesson the newest version dropped can't be used by a Question in use."""
    make_content()

    def newer(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["version"] = "v2026-02-01"
        syllabus["materials"] = syllabus["materials"][1:]  # drops mat-docs
        syllabus["weeks"][0]["lessons"][0]["materials"] = ["mat-video"]
        syllabus["weeks"][0]["milestones"][0]["materials"] = []

    problems = check_folder(make_content(newer), baseline=None)

    assert (
        "w01-l01-q01: unknown material 'mat-docs': a Question's Materials must be in the "
        "Stack's newest Syllabus (v2026-02-01)"
    ) in errors(problems)


def test_a_version_folder_with_its_own_question_banks_is_refused(
    make_content: ContentFactory,
) -> None:
    folder = make_content()
    (folder / "questions").mkdir()

    [problem] = [p for p in check_folder(folder, baseline=None) if p.level == "error"]

    assert Path(problem.file) == folder / "questions"
    assert problem.message.startswith("Question Banks no longer live in version folders")


def test_a_concept_can_be_declared_in_another_file(make_content: ContentFactory) -> None:
    other = make_bank("w01-l02", "second")
    other["questions"][0]["concept"] = "concept-a"  # declared in w01-l01's file
    other["questions"][1]["concept"] = "concept-a"
    other["concepts"] = other["concepts"][1:]  # second-a has no Questions left

    assert errors(check_folder(make_content(extra_banks={"w01-l02": other}), baseline=None)) == []


# --- Against the git baseline ----------------------------------------------------------------


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repository holding the test Stack, committed: the baseline."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    write_bank(root, copy.deepcopy(BANK))
    commit(root)
    return root


def stack_dir(root: Path) -> Path:
    return root / "content" / "mini-stack"


def write_bank(root: Path, bank: dict[str, Any], **extra: dict[str, Any]) -> Path:
    return write_folder(root / "content", copy.deepcopy(SYLLABUS), {LESSON: bank, **extra})


def commit(root: Path) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "content")


def bank_now(root: Path) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(
        (stack_dir(root) / "question-bank" / f"{LESSON}.json").read_text(encoding="utf-8")
    )
    return doc


def check_repo(root: Path, today: date = TODAY, baseline: str = "HEAD") -> list[Problem]:
    return check_stack(stack_dir(root), baseline=baseline, today=today)


def test_the_committed_bank_passes(repo: Path) -> None:
    assert errors(check_repo(repo)) == []


def test_a_deleted_question_is_refused(repo: Path) -> None:
    bank = bank_now(repo)
    bank["questions"].pop(0)
    bank["questions"].append(extra_question("w01-l01-q09"))
    write_bank(repo, bank)

    problems = [p for p in check_repo(repo) if p.item == "w01-l01-q01"]

    assert [(p.level, Path(p.file), p.message) for p in problems] == [
        (
            "error",
            stack_dir(repo) / "question-bank" / f"{LESSON}.json",
            "deleted since HEAD: a committed Question is never deleted; retire it instead",
        )
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("prompt", "A better prompt?"),
        ("answer", "b"),
        ("concept", "concept-b"),
        ("materials", []),
        ("sources", [source(2)]),
    ],
)
def test_any_edit_but_retiring_or_retagging_is_refused(repo: Path, field: str, value: Any) -> None:
    bank = bank_now(repo)
    bank["questions"][0][field] = value
    write_bank(repo, bank)

    assert (
        f"w01-l01-q01: changed since HEAD ({field}): a committed Question is never edited; retire "
        "it (replaced_by a new Question) or change only its Lesson tag"
    ) in errors(check_repo(repo))


def test_retiring_and_retagging_are_allowed(repo: Path) -> None:
    bank = bank_now(repo)
    retire(bank["questions"][0], replaced_by="w01-l01-q09")
    bank["questions"].append(
        mc_question("w01-l01-q09", "concept-a") | {"sources": [source(3, "2026-01-02")]}
    )
    bank["questions"][2]["lesson"] = "w01-l02"
    write_bank(repo, bank)

    problems = check_repo(repo)

    assert errors(problems) == [
        "w01-l01: the Lesson has 7 Questions that aren't retired; needs at least 8",
        "w01-l02: the Lesson has 1 Questions that aren't retired; needs at least 8",
        "w01-l02: a Lesson Quiz needs 4 multiple-choice and 2 written Questions; the Lesson has 1 "
        "and 0 that aren't retired",
    ]  # only the minimums: moving a Question is allowed, it just leaves w01-l01 short


def test_a_retirement_is_final(repo: Path) -> None:
    bank = bank_now(repo)
    retire(bank["questions"][0])
    bank["questions"].append(extra_question("w01-l01-q09") | {"sources": [source(1, "2026-01-02")]})
    write_bank(repo, bank)
    commit(repo)

    del bank["questions"][0]["retired"]
    write_bank(repo, bank)
    undone = errors(check_repo(repo))
    bank["questions"][0]["retired"] = {"reason": "Another reason."}
    write_bank(repo, bank)
    edited = errors(check_repo(repo))

    message = (
        "w01-l01-q01: its retirement changed since HEAD: a retirement is final, and never edited "
        "or undone"
    )
    assert undone == [message]
    assert edited == [message]


@pytest.mark.parametrize(
    ("accessed", "passes"),
    [("2026-01-02", True), ("2026-01-01", True), ("2025-12-31", False), ("2026-01-03", False)],
)
def test_a_new_questions_sources_are_from_this_run(repo: Path, accessed: str, passes: bool) -> None:
    """Today or yesterday in UTC, so a run that crosses 00:00 UTC still passes."""
    bank = bank_now(repo)
    bank["questions"].append(
        mc_question("w01-l01-q09", "concept-a") | {"sources": [source(1), source(2, accessed)]}
    )
    bank["questions"][-1]["sources"][0]["accessed"] = "2026-01-02"
    write_bank(repo, bank)

    found = errors(check_repo(repo))

    assert found == (
        []
        if passes
        else [
            f"w01-l01-q09: sources/1/accessed: {accessed} is not in this run; a new Question's "
            "Sources are accessed today or yesterday (UTC: 2026-01-01 or 2026-01-02)"
        ]
    )


def test_committed_questions_keep_their_old_sources(repo: Path) -> None:
    """The run rule is for new Questions: committed ones were checked when they were new."""
    assert SOURCES_ACCESSED == "2026-01-01"
    assert errors(check_repo(repo, today=date(2026, 9, 26))) == []


def test_a_new_question_on_a_tested_concept_is_a_warning_naming_one(repo: Path) -> None:
    bank = bank_now(repo)
    bank["questions"].append(
        mc_question("w01-l01-q09", "concept-b") | {"sources": [source(1, "2026-01-02")]}
    )
    bank["concepts"].append({"id": "concept-new", "name": "New"})
    bank["questions"] += [
        mc_question(f"w01-l01-q1{n}", "concept-new") | {"sources": [source(1, "2026-01-02")]}
        for n in (0, 1)
    ]
    write_bank(repo, bank)

    problems = check_repo(repo)

    assert errors(problems) == []
    assert warnings(problems) == [
        "1 lessons: no Questions yet (first: w01-l02)",
        "w01-l01-q09: tests the Concept 'concept-b', which w01-l01-q03 already tests: a repeat "
        "is allowed, but make sure it is deliberate",
    ]


def test_new_questions_on_a_new_concept_are_no_warning(tmp_path: Path) -> None:
    """A Stack with nothing committed yet: every Question is new, and none repeats."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    bank = copy.deepcopy(BANK)
    for q in bank["questions"]:
        q["sources"] = [source(1, "2026-01-02")]
    write_bank(root, bank)

    problems = check_repo(root)

    assert errors(problems) == []
    assert not [w for w in warnings(problems) if "tests the Concept" in w]


def test_without_git_the_baseline_rules_are_skipped_and_say_so(
    make_content: ContentFactory,
) -> None:
    problems = check_folder(make_content(), today=date(2030, 1, 1))

    assert errors(problems) == []
    [skipped] = [p for p in problems if p.item == "(baseline)"]
    assert skipped.level == "warning"
    assert skipped.message.startswith("no git baseline (")


def test_an_unknown_baseline_ref_is_an_error(repo: Path) -> None:
    assert errors(check_repo(repo, baseline="no-such-branch")) == [
        "(baseline): git ref 'no-such-branch' doesn't name a commit"
    ]


def test_the_baseline_can_be_an_earlier_commit(repo: Path) -> None:
    """CI passes a pull request's base: the rules hold across all its commits."""
    base = git(repo, "rev-parse", "HEAD").strip()
    bank = bank_now(repo)
    bank["questions"][0]["prompt"] = "Edited and committed."
    write_bank(repo, bank)
    commit(repo)

    assert errors(check_repo(repo)) == []  # nothing changed since HEAD
    assert "changed since" in errors(check_repo(repo, baseline=base))[0]


def test_a_baseline_in_the_old_layout_lets_questions_gain_sources_once(tmp_path: Path) -> None:
    """The one-time move out of version folders: the committed Questions had no Sources, lived
    in `<version>/questions/<lesson>.json` and were tagged by that file. Nothing had been
    released, so a slip that writing the Sources turned up may be fixed on the way, but it is
    reported."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    version = stack_dir(root) / "v2026-01-01"
    (version / "questions").mkdir(parents=True)
    (version / "syllabus.json").write_text(json.dumps(SYLLABUS), encoding="utf-8")
    legacy = copy.deepcopy(BANK) | {"schema_version": 1, "lesson_id": LESSON}
    for q in legacy["questions"]:
        del q["sources"], q["lesson"]
    (version / "questions" / f"{LESSON}.json").write_text(json.dumps(legacy), encoding="utf-8")
    commit(root)

    git(root, "rm", "-q", "-r", "content/mini-stack/v2026-01-01/questions")
    bank = copy.deepcopy(BANK)
    bank["questions"][1]["prompt"] = "Edited on the way."
    write_bank(root, bank)

    problems = check_repo(root, today=date(2026, 9, 26))
    assert errors(problems) == []
    assert (
        "w01-l01-q02: changed since HEAD (prompt), which is allowed only in the one-time move out "
        "of version folders; from now on a committed Question is never edited"
    ) in warnings(problems)


def test_a_question_deleted_in_the_move_is_still_refused(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    version = stack_dir(root) / "v2026-01-01"
    (version / "questions").mkdir(parents=True)
    (version / "syllabus.json").write_text(json.dumps(SYLLABUS), encoding="utf-8")
    legacy = copy.deepcopy(BANK) | {"schema_version": 1, "lesson_id": LESSON}
    for q in legacy["questions"]:
        del q["sources"], q["lesson"]
    (version / "questions" / f"{LESSON}.json").write_text(json.dumps(legacy), encoding="utf-8")
    commit(root)

    git(root, "rm", "-q", "-r", "content/mini-stack/v2026-01-01/questions")
    bank = copy.deepcopy(BANK)
    del bank["questions"][1]
    write_bank(root, bank)

    assert any("deleted since HEAD" in e for e in errors(check_repo(root, today=TODAY)))


def test_cli_takes_the_baseline_and_the_day(repo: Path) -> None:
    bank = bank_now(repo)
    bank["questions"].append(
        mc_question("w01-l01-q09", "concept-a") | {"sources": [source(1, "2026-01-02")]}
    )
    write_bank(repo, bank)

    args = [str(repo / "content"), "--baseline", "HEAD"]
    assert check.main([*args, "--today", "2026-01-02"]) == 0
    assert check.main([*args, "--today", "2026-01-04"]) == 1
