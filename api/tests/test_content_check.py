from pathlib import Path

import httpx
import pytest

from app.config import REPO_ROOT
from app.content import check
from app.content.check import Problem, check_folder, check_stack
from tests.conftest import ContentFactory, make_bank


def error_problems(folder: Path, **kwargs: bool) -> list[Problem]:
    return [p for p in check_folder(folder, **kwargs) if p.level == "error"]


def errors(folder: Path, **kwargs: bool) -> list[str]:
    return [f"{p.item}: {p.message}" for p in error_problems(folder, **kwargs)]


def the_error_for(item: str, folder: Path) -> Problem:
    [problem] = [p for p in error_problems(folder) if p.item == item]
    return problem


def test_valid_folder_passes(make_content: ContentFactory) -> None:
    assert errors(make_content()) == []


def test_lesson_without_questions_is_only_a_warning(make_content: ContentFactory) -> None:
    problems = check_folder(make_content(), baseline=None)
    assert [p.level for p in problems] == ["warning"]
    assert (problems[0].item, problems[0].message) == (
        "1 lessons",
        "no Questions yet (first: w01-l02)",
    )


def test_format_violation_names_the_item(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        del syllabus["weeks"][0]["lessons"][0]["topics"]

    folder = make_content(edit)
    [problem] = error_problems(folder)
    assert Path(problem.file) == folder / "syllabus.json"
    assert problem.item == "w01-l01"
    assert problem.message == "weeks/0/lessons/0/topics: Field required"


def test_format_violation_in_a_question_bank_names_the_question(
    make_content: ContentFactory,
) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["questions"][2]["answer"] = "z"  # not a choice ID at all

    folder = make_content(edit)
    [problem] = error_problems(folder)
    assert Path(problem.file) == folder.parent / "question-bank" / "w01-l01.json"
    assert problem.item == "w01-l01-q03"
    assert problem.message.startswith("questions/2/multiple_choice/answer: String should match")


def test_format_violation_in_a_choice_names_the_question(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["questions"][1]["choices"][1]["id"] = "z"

    [problem] = error_problems(make_content(edit))
    assert problem.item == "w01-l01-q02"
    assert problem.message.startswith("questions/1/multiple_choice/choices/1/id: ")


def test_format_violation_outside_any_item_names_the_field(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        syllabus["version"] = "2026-01-01"

    [problem] = error_problems(make_content(edit))
    assert problem.item == "version"
    assert problem.message.startswith("String should match pattern")


def test_file_that_is_not_json_is_named(make_content: ContentFactory) -> None:
    folder = make_content()
    bank_file = folder.parent / "question-bank" / "w01-l01.json"
    bank_file.write_text("{ not json", encoding="utf-8")

    [problem] = error_problems(folder)
    assert Path(problem.file) == bank_file
    assert problem.item == "(file)"
    assert problem.message.startswith("invalid JSON at line 1")


def test_duplicate_permanent_id(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        syllabus["weeks"][0]["lessons"][1]["id"] = "w01-l01"

    folder = make_content(edit)
    problem = the_error_for("w01-l01", folder)
    assert Path(problem.file) == folder / "syllabus.json"
    assert problem.message == (
        "duplicate permanent id (Lesson): already used by a Lesson in syllabus.json"
    )


def test_folder_must_match_the_stack_id_and_version(
    make_content: ContentFactory, tmp_path: Path
) -> None:
    folder = make_content()  # <tmp>/mini-stack/v2026-01-01
    wrong_version = folder.rename(tmp_path / "mini-stack" / "v2026-02-02")
    problem = the_error_for("v2026-01-01", wrong_version)
    assert Path(problem.file) == wrong_version / "syllabus.json"
    assert problem.message == "version doesn't match its folder name 'v2026-02-02'"

    (tmp_path / "other-stack").mkdir()
    wrong_stack = wrong_version.rename(tmp_path / "other-stack" / "v2026-01-01")
    assert the_error_for("mini-stack", wrong_stack).message == (
        "Stack id doesn't match its folder name 'other-stack'; "
        "a Stack's versions live in content/<stack-id>/<version>/"
    )


def test_duplicate_concept_id_in_one_bank(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["concepts"].append({"id": "concept-a", "name": "Again"})

    folder = make_content(edit)
    problem = the_error_for("concept-a", folder)
    assert Path(problem.file) == folder.parent / "question-bank" / "w01-l01.json"
    assert problem.message == (
        "duplicate permanent id (Concept): already used by a Concept in question-bank/w01-l01.json"
    )


def test_concept_id_reused_in_another_bank_names_both_files(
    make_content: ContentFactory,
) -> None:
    other = make_bank("w01-l02")  # the same concept-a..d IDs as w01-l01's bank
    folder = make_content(extra_banks={"w01-l02": other})

    reuses = [p for p in error_problems(folder) if p.item.startswith("concept-")]
    assert sorted(p.item for p in reuses) == ["concept-a", "concept-b", "concept-c", "concept-d"]
    for p in reuses:
        assert Path(p.file) == folder.parent / "question-bank" / "w01-l02.json"
        assert p.message == (
            "duplicate permanent id (Concept): already used by a Concept in "
            "question-bank/w01-l01.json"
        )


def test_ids_are_unique_across_kinds(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["concepts"][0]["id"] = "w01-l02"  # the second Lesson's ID
        for q in bank["questions"]:
            if q["concept"] == "concept-a":
                q["concept"] = "w01-l02"

    folder = make_content(edit)
    problem = the_error_for("w01-l02", folder)
    assert Path(problem.file) == folder.parent / "question-bank" / "w01-l01.json"
    assert problem.message == (
        "duplicate permanent id (Concept): already used by a Lesson in v2026-01-01/syllabus.json"
    )


def test_duplicate_question_id(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["questions"][1]["id"] = bank["questions"][0]["id"]

    folder = make_content(edit)
    problem = the_error_for("w01-l01-q01", folder)
    assert Path(problem.file) == folder.parent / "question-bank" / "w01-l01.json"
    assert problem.message == (
        "duplicate permanent id (Question): already used by a Question in "
        "question-bank/w01-l01.json"
    )


def test_question_id_reused_in_another_bank_names_both_files(
    make_content: ContentFactory,
) -> None:
    other = make_bank("w01-l02", concept_prefix="other")
    other["questions"][0]["id"] = "w01-l01-q01"
    folder = make_content(extra_banks={"w01-l02": other})

    problem = the_error_for("w01-l01-q01", folder)
    assert Path(problem.file) == folder.parent / "question-bank" / "w01-l02.json"
    assert problem.message == (
        "duplicate permanent id (Question): already used by a Question in "
        "question-bank/w01-l01.json"
    )


def test_concept_needs_two_questions(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["concepts"].append({"id": "concept-e", "name": "Lonely"})
        bank["questions"][0]["concept"] = "concept-e"

    folder = make_content(edit)
    for concept in ("concept-a", "concept-e"):
        problem = the_error_for(concept, folder)
        assert Path(problem.file) == folder.parent / "question-bank" / "w01-l01.json"
        assert problem.message == (
            "Concept has 1 Question(s) that aren't retired; needs at least 2 so a Retake always "
            "has a sibling"
        )


def test_unknown_material_reference(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        syllabus["weeks"][0]["milestones"][0]["materials"] = ["nope"]

    assert "w01-m01: unknown material 'nope'" in errors(make_content(edit))


def test_answer_must_be_a_choice(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["questions"][0]["answer"] = "c"

    assert "w01-l01-q01: answer is not one of the choices" in errors(make_content(edit))


def test_lesson_must_support_a_lesson_quiz(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["questions"][6]["type"] = "multiple_choice"  # leaves only one written Question
        bank["questions"][6]["choices"] = [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}]
        bank["questions"][6]["answer"] = "a"
        del bank["questions"][6]["model_answer"]

    assert any("needs 4 multiple-choice and 2 written" in e for e in errors(make_content(edit)))


def test_question_tagged_to_an_unknown_lesson(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["questions"][0]["lesson"] = "w09-l09"

    assert (
        "w01-l01-q01: lesson 'w09-l09' is not in the Stack's newest Syllabus (v2026-01-01); "
        "re-tag the Question, or retire it"
    ) in errors(make_content(edit))


def test_dead_link_is_an_error_and_blocked_site_a_warning(
    make_content: ContentFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    statuses = {"https://example.com/docs": 404, "https://example.com/video": 403}

    def fake_get(self: httpx.Client, url: str) -> httpx.Response:
        return httpx.Response(statuses[url], request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    folder = make_content()
    problems = check_folder(folder, links=True)
    by_item = {p.item: p for p in problems}
    assert by_item["mat-docs"].level == "error"
    assert Path(by_item["mat-docs"].file) == folder / "syllabus.json"
    assert by_item["mat-docs"].message == "link doesn't load: HTTP 404 (https://example.com/docs)"
    assert by_item["mat-video"].level == "warning"


def test_link_that_cannot_connect_is_an_error(
    make_content: ContentFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(self: httpx.Client, url: str) -> httpx.Response:
        if url == "https://example.com/video":
            raise httpx.ConnectError("no route to host")
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    [problem] = error_problems(make_content(), links=True)
    assert problem.item == "mat-video"
    assert problem.message == "link doesn't load: ConnectError (https://example.com/video)"


def test_links_are_not_checked_without_the_flag(
    make_content: ContentFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_network(self: httpx.Client, url: str) -> httpx.Response:
        raise AssertionError("the network was used")

    monkeypatch.setattr(httpx.Client, "get", no_network)
    assert errors(make_content()) == []


def test_cli_exit_code(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["questions"][0]["answer"] = "z"

    assert check.main([str(make_content())]) == 0
    assert check.main([str(make_content(edit))]) == 1


def test_cli_finds_version_folders_under_a_content_root(
    make_content: ContentFactory, tmp_path: Path
) -> None:
    folder = make_content()  # <tmp>/mini-stack/v2026-01-01
    assert check.main([str(folder.parent.parent)]) == 0
    assert check.main([str(tmp_path / "empty")]) == 1


@pytest.mark.parametrize(
    "stack",
    sorted(p for p in (REPO_ROOT / "content").iterdir() if p.name != "schema"),
    ids=lambda p: p.name,
)
def test_committed_content_passes(stack: Path) -> None:
    assert [f"{p.item}: {p.message}" for p in check_stack(stack) if p.level == "error"] == []
