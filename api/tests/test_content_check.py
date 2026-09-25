from pathlib import Path

import httpx
import pytest

from app.config import REPO_ROOT
from app.content import check
from app.content.check import check_folder
from tests.conftest import ContentFactory


def errors(folder: Path, **kwargs: bool) -> list[str]:
    return [f"{p.item}: {p.message}" for p in check_folder(folder, **kwargs) if p.level == "error"]


def test_valid_folder_passes(make_content: ContentFactory) -> None:
    assert errors(make_content()) == []


def test_lesson_without_question_bank_is_only_a_warning(make_content: ContentFactory) -> None:
    problems = check_folder(make_content())
    assert [p.level for p in problems] == ["warning"]
    assert "no Question Bank yet" in problems[0].message


def test_format_violation_names_the_item(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        del syllabus["weeks"][0]["lessons"][0]["topics"]

    [problem] = errors(make_content(edit))
    assert problem.startswith("weeks/0/lessons/0")
    assert problem == "weeks/0/lessons/0/topics: Field required"


def test_duplicate_permanent_id(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        syllabus["weeks"][0]["lessons"][1]["id"] = "w01-l01"

    assert "w01-l01: duplicate permanent id" in errors(make_content(edit))


def test_duplicate_question_id(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["questions"][1]["id"] = bank["questions"][0]["id"]

    assert "w01-l01-q01: duplicate question id" in errors(make_content(edit))


def test_concept_needs_two_questions(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["concepts"].append({"id": "concept-e", "name": "Lonely"})
        bank["questions"][0]["concept"] = "concept-e"

    found = errors(make_content(edit))
    assert any(e.startswith("concept-a: Concept has 1 Question") for e in found)
    assert any(e.startswith("concept-e: Concept has 1 Question") for e in found)


def test_unknown_material_reference(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        syllabus["weeks"][0]["milestones"][0]["materials"] = ["nope"]

    assert "w01-m01: unknown material 'nope'" in errors(make_content(edit))


def test_answer_must_be_a_choice(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["questions"][0]["answer"] = "c"

    assert "w01-l01-q01: answer is not one of the choices" in errors(make_content(edit))


def test_bank_must_support_a_lesson_quiz(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["questions"][6]["type"] = "multiple_choice"  # leaves only one written Question
        bank["questions"][6]["choices"] = [{"id": "a", "text": "x"}, {"id": "b", "text": "y"}]
        bank["questions"][6]["answer"] = "a"
        del bank["questions"][6]["model_answer"]

    assert any("needs 4 multiple-choice and 2 written" in e for e in errors(make_content(edit)))


def test_bank_for_unknown_lesson(make_content: ContentFactory) -> None:
    def edit(syllabus: dict, bank: dict) -> None:
        bank["lesson_id"] = "w09-l09"

    assert "w09-l09: lesson_id is not in the Syllabus" in errors(make_content(edit))


def test_dead_link_is_an_error_and_blocked_site_a_warning(
    make_content: ContentFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    statuses = {"https://example.com/docs": 404, "https://example.com/video": 403}

    def fake_get(self: httpx.Client, url: str) -> httpx.Response:
        return httpx.Response(statuses[url], request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    problems = check_folder(make_content(), links=True)
    by_item = {p.item: p for p in problems}
    assert by_item["mat-docs"].level == "error"
    assert by_item["mat-video"].level == "warning"


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
    "folder",
    sorted((REPO_ROOT / "content").glob("*/v*")),
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def test_committed_content_passes(folder: Path) -> None:
    assert errors(folder) == []
