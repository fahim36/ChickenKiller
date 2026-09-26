"""The content check's rules for Upcoming Challenges (#16): each Daily Challenge file has a
number, a UTC date consecutive from the Stack's launch, and three Questions of its Question Bank
(two multiple choice, one written). Against the git baseline a released Challenge is frozen:
never changed or deleted. Each Stack's line says how far ahead Challenges are written, and warns
below three Days. The clock is the `today` passed to the check."""

import copy
import json
import subprocess
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from app.content import check
from app.content.check import Problem, check_stack
from tests.conftest import (
    BANK,
    CHALLENGE_MIX,
    LAUNCH,
    LESSON,
    SYLLABUS,
    challenge,
    mc_question,
    source,
    write_challenges,
    write_folder,
    write_json,
)

TODAY = date(2026, 1, 3)
"""The day of the test run: #1 (2026-01-01) to #3 (today's) are released, #4 is upcoming."""

MIX = CHALLENGE_MIX


def errors(problems: list[Problem]) -> list[str]:
    return [f"{p.item}: {p.message}" for p in problems if p.level == "error"]


def warnings(problems: list[Problem]) -> list[str]:
    return [f"{p.item}: {p.message}" for p in problems if p.level == "warning"]


def day_of(number: int) -> str:
    """#n of a Stack launched on LAUNCH."""
    return str(challenge(number)["date"])


def week(*numbers: int) -> list[dict[str, Any]]:
    return [challenge(n) for n in numbers]


@pytest.fixture
def stack(tmp_path: Path) -> Path:
    """The test Stack, outside git (no baseline)."""
    return write_folder(tmp_path, copy.deepcopy(SYLLABUS), {LESSON: copy.deepcopy(BANK)}).parent


def check_here(stack: Path, today: date = TODAY) -> list[Problem]:
    return check_stack(stack, baseline=None, today=today)


# --- The files ---------------------------------------------------------------------------------


def test_challenges_consecutive_from_launch_pass(stack: Path) -> None:
    write_challenges(stack, *week(1, 2, 3, 4, 5))

    assert errors(check_here(stack)) == []


def test_a_day_with_no_challenge_written_is_allowed(stack: Path) -> None:
    write_challenges(stack, *week(1, 2, 5))

    assert errors(check_here(stack)) == []


def test_a_challenges_date_follows_from_its_number(stack: Path) -> None:
    write_challenges(stack, challenge(1, LAUNCH), challenge(2, "2026-01-03"))

    assert errors(check_here(stack)) == [
        "#2: dated 2026-01-03, but #2 of a Stack launched on 2026-01-01 is 2026-01-02: "
        "Challenge n is on the launch Day plus n - 1 Days",
    ]


def test_a_challenge_file_is_named_by_its_number(stack: Path) -> None:
    folder = write_challenges(stack, *week(1))
    (folder / "001.json").rename(folder / "1.json")

    assert errors(check_here(stack)) == ["#1: the file for Challenge #1 is named 001.json"]


def test_challenges_need_the_stacks_launch_date(stack: Path) -> None:
    write_challenges(stack, *week(1), launch=None)

    assert errors(check_here(stack)) == [
        "(file): missing: the Stack's launch Day, which numbers its Daily Challenges",
    ]


def test_a_challenge_has_exactly_three_questions(stack: Path) -> None:
    write_challenges(stack, challenge(1, LAUNCH, MIX[:2]))

    [error] = errors(check_here(stack))

    assert error.startswith("(root)") or error.startswith("questions: ")
    assert "at least 3 items" in error


def test_a_challenge_is_two_multiple_choice_and_one_written(stack: Path) -> None:
    write_challenges(stack, challenge(1, LAUNCH, ["w01-l01-q01", "w01-l01-q07", "w01-l01-q08"]))

    assert errors(check_here(stack)) == [
        "#1: a Daily Challenge is 2 multiple-choice Questions and 1 written; this one has 1 and 2",
    ]


def test_a_challenges_questions_are_in_the_question_bank(stack: Path) -> None:
    write_challenges(stack, challenge(1, LAUNCH, ["w01-l01-q01", "no-such-question", MIX[2]]))

    assert errors(check_here(stack)) == [
        "#1: 'no-such-question' is not a Question in the Stack's Question Bank",
    ]


def test_a_challenge_lists_a_question_once(stack: Path) -> None:
    write_challenges(stack, challenge(1, LAUNCH, [MIX[0], MIX[0], MIX[2]]))

    [error] = errors(check_here(stack))

    assert "listed more than once: w01-l01-q01" in error


def test_an_upcoming_challenge_cant_use_a_retired_question(stack: Path) -> None:
    bank_file = stack / "question-bank" / f"{LESSON}.json"
    bank = json.loads(bank_file.read_text(encoding="utf-8"))
    bank["questions"][0]["retired"] = {"reason": "Out of date."}
    bank["questions"].append(mc_question("w01-l01-q09", "concept-a"))
    write_json(bank_file, bank)
    write_challenges(stack, *week(1, 4))

    assert errors(check_here(stack)) == [
        "#4: w01-l01-q01 is a Retired Question, which can't be answered; "
        "an Upcoming Challenge uses Questions that aren't retired",
    ]


# --- How far ahead Challenges are written --------------------------------------------------------


@pytest.mark.parametrize(
    ("last", "today", "line", "warns"),
    [
        (5, date(2026, 1, 1), "Challenges written through 2026-01-05 (5 Days left)", False),
        (5, date(2026, 1, 3), "Challenges written through 2026-01-05 (3 Days left)", False),
        (5, date(2026, 1, 4), "Challenges written through 2026-01-05 (2 Days left)", True),
        (5, date(2026, 1, 5), "Challenges written through 2026-01-05 (1 Day left)", True),
        (5, date(2026, 1, 9), "Challenges written through 2026-01-05 (0 Days left)", True),
    ],
)
def test_days_left_count_from_today_to_the_last_challenge_written(
    stack: Path, last: int, today: date, line: str, warns: bool
) -> None:
    write_challenges(stack, *week(*range(1, last + 1)))

    assert str(check.challenges_ahead(stack, today)) == line
    days_left = [w for w in warnings(check_here(stack, today)) if "Days" in w or "Day " in w]
    assert days_left == (
        [f"(challenges): {line}: write more with /write-challenges; fewer than 3 Days are left"]
        if warns
        else []
    )


def test_a_gap_doesnt_shorten_the_days_left(stack: Path) -> None:
    write_challenges(stack, *week(1, 5))

    assert str(check.challenges_ahead(stack, date(2026, 1, 2))) == (
        "Challenges written through 2026-01-05 (4 Days left)"
    )


def test_a_launched_stack_with_no_challenge_written_warns(stack: Path) -> None:
    write_challenges(stack)

    assert str(check.challenges_ahead(stack, TODAY)) == "No Challenges written (0 Days left)"
    assert "(challenges): No Challenges written (0 Days left)" in " ".join(
        warnings(check_here(stack))
    )


def test_a_stack_with_no_challenges_folder_has_no_line(stack: Path) -> None:
    assert check.challenges_ahead(stack, TODAY) is None
    assert errors(check_here(stack)) == []


def test_the_check_prints_each_stacks_line(stack: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_challenges(stack, *week(1, 2, 3, 4, 5))

    code = check.main([str(stack), "--today", "2026-01-02"])

    assert code == 0
    assert f"{stack}: Challenges written through 2026-01-05 (4 Days left)" in (
        capsys.readouterr().out.splitlines()
    )


# --- Against the git baseline: released Challenges are frozen ------------------------------------


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
    """A git repository holding the test Stack with Challenges #1 to #4, committed."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    stack = write_folder(
        root / "content", copy.deepcopy(SYLLABUS), {LESSON: copy.deepcopy(BANK)}
    ).parent
    write_challenges(stack, *week(1, 2, 3, 4))
    commit(root)
    return stack


def commit(root: Path) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "content")


def check_repo(stack: Path, today: date = TODAY) -> list[Problem]:
    return check_stack(stack, baseline="HEAD", today=today)


def test_the_committed_challenges_pass(repo: Path) -> None:
    assert errors(check_repo(repo)) == []


def test_a_released_challenge_is_frozen(repo: Path) -> None:
    edited = challenge(2, day_of(2), ["w01-l01-q02", "w01-l01-q03", "w01-l01-q07"])
    write_challenges(repo, *week(1), edited, *week(3, 4))

    assert errors(check_repo(repo)) == [
        "#2: changed since HEAD, but its Day (2026-01-02) has begun: a released Daily "
        "Challenge is frozen",
    ]


def test_a_released_challenge_is_frozen_byte_for_byte(repo: Path) -> None:
    path = repo / "challenges" / "001.json"
    path.write_text(json.dumps(challenge(1, LAUNCH)) + "\n", encoding="utf-8", newline="\n")

    assert [e.split(":")[0] for e in errors(check_repo(repo))] == ["#1"]


def test_line_endings_dont_count(repo: Path) -> None:
    path = repo / "challenges" / "001.json"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

    assert errors(check_repo(repo)) == []


def test_a_released_challenge_cant_be_deleted(repo: Path) -> None:
    write_challenges(repo, *week(2, 3, 4))

    assert errors(check_repo(repo)) == [
        "#1: deleted since HEAD, but its Day (2026-01-01) has begun: a released Daily "
        "Challenge is frozen",
    ]


OTHER = ["w01-l01-q02", "w01-l01-q04", "w01-l01-q08"]


def test_a_future_challenge_can_be_edited(repo: Path) -> None:
    write_challenges(repo, *week(1, 2, 3), challenge(4, day_of(4), OTHER))

    assert errors(check_repo(repo)) == []


def test_a_future_challenge_can_be_deleted(repo: Path) -> None:
    write_challenges(repo, *week(1, 2, 3))

    assert errors(check_repo(repo)) == []


def test_todays_challenge_is_released_and_frozen(repo: Path) -> None:
    """A Challenge is released at 00:00 UTC on its own Day, so today's can't change."""
    write_challenges(repo, *week(1, 2), challenge(3, day_of(3), OTHER), *week(4))

    assert errors(check_repo(repo)) == [
        "#3: changed since HEAD, but its Day (2026-01-03) has begun: a released Daily "
        "Challenge is frozen",
    ]


@pytest.mark.parametrize(
    ("now", "frozen"),
    [
        (datetime(2026, 1, 3, 23, 59, 59, tzinfo=UTC), False),
        (datetime(2026, 1, 4, 0, 0, 0, tzinfo=UTC), True),
    ],
)
def test_a_challenge_freezes_at_midnight_utc_on_its_day(
    repo: Path, now: datetime, frozen: bool
) -> None:
    """#4 (2026-01-04) is editable until 23:59:59 UTC the Day before, and frozen from 00:00."""
    write_challenges(repo, *week(1, 2, 3), challenge(4, day_of(4), OTHER))

    found = [e.split(":")[0] for e in errors(check_repo(repo, today=now.astimezone(UTC).date()))]

    assert found == (["#4"] if frozen else [])


@pytest.mark.parametrize("number", [2, 3])
def test_a_new_challenge_for_a_day_that_has_begun_is_refused(repo: Path, number: int) -> None:
    """Earlier Days and today alike: a Day that had no Challenge at 00:00 UTC has none."""
    git(repo.parents[1], "rm", "-q", str(repo / "challenges" / f"{number:03}.json"))
    commit(repo.parents[1])
    write_challenges(repo, *week(1, 2, 3, 4))

    assert errors(check_repo(repo)) == [
        f"#{number}: written for {day_of(number)}, a Day that has begun: a Day with no Challenge "
        "written has no Challenge",
    ]


def test_moving_the_launch_date_is_caught_by_the_frozen_challenges(repo: Path) -> None:
    write_challenges(repo, *week(1, 2, 3, 4), launch="2026-01-02")

    assert [e.split(":")[0] for e in errors(check_repo(repo))] == ["#1", "#2", "#3", "#4"]


@pytest.mark.parametrize(("accessed", "passes"), [("2026-01-03", True), ("2026-01-01", False)])
def test_a_new_challenge_questions_sources_are_from_this_run(
    repo: Path, accessed: str, passes: bool
) -> None:
    """A Question written for a Challenge is a new Question like any other, tagged to a Lesson or
    not: its Sources are accessed today or yesterday (UTC)."""
    bank_file = repo / "question-bank" / "challenge-005.json"
    new = [
        mc_question(f"c005-q0{n}", "c005-idea", lesson=None) | {"sources": [source(n, accessed)]}
        for n in (1, 2)
    ]
    write_json(
        bank_file,
        {"schema_version": 2, "concepts": [{"id": "c005-idea", "name": "Idea"}], "questions": new},
    )
    write_challenges(
        repo, *week(1, 2, 3, 4), challenge(5, day_of(5), ["c005-q01", "c005-q02", "w01-l01-q07"])
    )

    found = errors(check_repo(repo))

    assert found == (
        []
        if passes
        else [
            f"c005-q0{n}: sources/0/accessed: 2026-01-01 is not in this run; a new Question's "
            "Sources are accessed today or yesterday (UTC: 2026-01-02 or 2026-01-03)"
            for n in (1, 2)
        ]
    )
