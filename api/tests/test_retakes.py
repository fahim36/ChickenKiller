"""After a Lesson Quiz, over the API (#8): the results for each Missed Question, Retakes on a
sibling Question, the Lesson completing only once every Retake is correct, a fresh quiz below
the Pass Mark, and the record of Missed Questions the Daily Review reads (#9). The sibling and
drawing rules themselves are tested in test_lesson_quiz_rules.py."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from app import quizzes
from app.content.importer import import_folder
from tests.conftest import (
    LEARNER_EMAIL,
    ClientFactory,
    ContentFactory,
    changelog_entry,
    make_bank,
    make_changelog,
    onboard,
)
from tests.test_lesson_quiz import (
    QUIZ,
    answer_all,
    code,
    keys,
    learner_id,
    lesson_states,
    start,
    submit,
)

LESSON = "/stacks/mini-stack/lessons/w01-l01"
Edit = Callable[[dict[str, Any], dict[str, Any]], None]


def question_number(n: int) -> str:
    return f"w01-l01-q{n:02}"


def mc(n: int, concept: str) -> dict[str, Any]:
    return {
        "id": question_number(n),
        "concept": concept,
        "type": "multiple_choice",
        "prompt": f"Question {n}?",
        "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
        "answer": "a",
        "explanation": f"Because of {n}.",
        "materials": ["mat-docs"],
    }


def own_explanations(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    """Give every Question an Explanation of its own, so a test can tell whose is shown."""
    for question in bank["questions"]:
        question["explanation"] = f"Because of {question['id']}."


def five_on_concept_a(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    """Concept a gets five multiple-choice Questions (q01, q02, q09, q10, q11), so a Missed
    Question on it has four siblings; b and c keep two each."""
    own_explanations(syllabus, bank)
    bank["questions"] += [mc(n, "concept-a") for n in (9, 10, 11)]


def ten_multiple_choice(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    """Ten multiple-choice Questions (q01-q06 and q09-q12) and the two written ones: a fresh
    quiz after a first one can draw four new Questions, but has to repeat two."""
    concepts = ["concept-a", "concept-b", "concept-c", "concept-a"]
    bank["questions"] += [mc(n, concepts[n - 9]) for n in range(9, 13)]


def setup(session: Session, api: TestClient, make_content: ContentFactory, edit: Edit) -> None:
    import_folder(
        session, make_content(edit, extra_banks={"w01-l02": make_bank("w01-l02", "second")})
    )
    onboard(api)


@pytest.fixture
def learner(session: Session, api: TestClient, make_content: ContentFactory) -> TestClient:
    """A Learner on the mini Stack, whose w01-l01 bank has two multiple-choice Questions on each
    of Concepts a, b and c (q01-q02, q03-q04, q05-q06), and each Explanation its own."""
    setup(session, api, make_content, own_explanations)
    return api


CONCEPT_OF = {question_number(n): "abc"[(n - 1) // 2] for n in range(1, 7)}
CONCEPT_OF.update({question_number(n): "a" for n in (9, 10, 11)})


def concept_siblings(question_id: str) -> set[str]:
    return {q for q, c in CONCEPT_OF.items() if c == CONCEPT_OF[question_id]} - {question_id}


def miss(quiz: dict[str, Any], missed: list[str]) -> dict[str, str | None]:
    """Answer every Question correctly except those in `missed`."""
    return {q["id"]: ("b" if q["id"] in missed else "a") for q in quiz["questions"]}


def pass_missing_one(client: TestClient, concept: str = "a") -> tuple[str, dict[str, Any]]:
    """Take the quiz and pass it (5 of 6), missing one Question on `concept`."""
    quiz = start(client)
    missed = next(q["id"] for q in quiz["questions"] if CONCEPT_OF[q["id"]] == concept)
    response = submit(client, quiz, miss(quiz, [missed]))
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return missed, result


def answer_retake(client: TestClient, retake: dict[str, Any], answer: str | None) -> Response:
    return client.post(f"{LESSON}/retakes/{retake['id']}/answers", json={"answer": answer})


# --- The results screen ----------------------------------------------------------------------


def test_the_results_show_each_missed_question_with_the_answers_explanation_and_materials(
    learner: TestClient,
) -> None:
    quiz = start(learner)
    wrong, unanswered = quiz["questions"][0]["id"], quiz["questions"][1]["id"]
    answers = miss(quiz, [wrong])
    del answers[unanswered]

    result = submit(learner, quiz, answers).json()

    assert result["missed"] == [
        {
            "id": qid,
            "type": "multiple_choice",
            "prompt": f"Question {int(qid[-2:])}?",
            "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
            "response": response,
            "answer": "a",
            "model_answer": None,
            "explanation": f"Because of {qid}.",
            "materials": [
                {
                    "id": "mat-docs",
                    "title": "Some docs",
                    "url": "https://example.com/docs",
                    "type": "docs",
                }
            ],
        }
        for qid, response in [(wrong, "b"), (unanswered, None)]
    ]


def test_a_quiz_with_no_misses_completes_the_lesson_with_no_retakes(learner: TestClient) -> None:
    quiz = start(learner)

    result = submit(learner, quiz, answer_all(quiz)).json()

    assert (result["next_step"], result["lesson_completed"]) == ("completed", True)
    assert (result["missed"], result["retakes"]) == ([], [])
    assert lesson_states(learner) == {"w01-l01": "completed", "w01-l02": "unlocked"}


# --- Passing with Missed Questions: Retakes --------------------------------------------------


def test_passing_with_a_miss_leaves_a_retake_on_a_sibling_and_the_lesson_not_completed(
    learner: TestClient,
) -> None:
    missed, result = pass_missing_one(learner)

    assert (result["passed"], result["next_step"], result["lesson_completed"]) == (
        True,
        "retakes",
        False,
    )
    [retake] = result["retakes"]
    assert retake["missed_question_id"] == missed
    # Concept a has exactly two Questions here, q01 and q02, so the Retake is the other one.
    [sibling] = {question_number(1), question_number(2)} - {missed}
    assert retake["question"] == {
        "id": sibling,
        "type": "multiple_choice",
        "prompt": retake["question"]["prompt"],
        "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
    }
    assert lesson_states(learner) == {"w01-l01": "unlocked", "w01-l02": "locked"}


def test_a_retake_question_comes_without_its_answer(learner: TestClient) -> None:
    _, result = pass_missing_one(learner)

    assert keys(result["retakes"]).isdisjoint({"answer", "explanation", "model_answer"})


def test_starting_the_quiz_while_retakes_are_pending_points_at_them(
    learner: TestClient,
) -> None:
    _, result = pass_missing_one(learner)

    response = learner.post(QUIZ)

    assert code(response) == (409, "retakes_pending")
    assert response.json()["detail"]["attempt_id"] == result["attempt_id"]
    pending = learner.get(f"{QUIZ}/{result['attempt_id']}/retakes").json()
    assert pending == {
        "attempt_id": result["attempt_id"],
        "lesson_id": "w01-l01",
        "lesson_completed": False,
        "retakes": result["retakes"],
    }


def test_a_correct_retake_completes_the_lesson_and_unlocks_the_next(learner: TestClient) -> None:
    _, result = pass_missing_one(learner)
    [retake] = result["retakes"]

    answered = answer_retake(learner, retake, "a").json()

    assert answered["correct"] is True
    assert answered["next_question"] is None
    assert (answered["pending"], answered["lesson_completed"]) == (0, True)
    assert lesson_states(learner) == {"w01-l01": "completed", "w01-l02": "unlocked"}
    assert learner.post("/stacks/mini-stack/lessons/w01-l02/quiz").status_code == 200


def test_a_wrong_retake_shows_its_explanation_and_offers_another_sibling(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    setup(session, api, make_content, five_on_concept_a)
    missed, result = pass_missing_one(api)
    [retake] = result["retakes"]
    first = retake["question"]["id"]
    assert first in concept_siblings(missed)

    answered = answer_retake(api, retake, "b").json()

    assert answered["correct"] is False
    assert answered["question"]["id"] == first
    assert answered["question"]["response"] == "b"
    assert answered["question"]["answer"] == "a"
    assert answered["question"]["explanation"] == f"Because of {first}."
    assert answered["next_question"]["id"] in concept_siblings(missed) - {first}
    assert (answered["pending"], answered["lesson_completed"]) == (1, False)
    assert lesson_states(api)["w01-l01"] == "unlocked"


def test_wrong_retakes_cycle_through_the_siblings_and_never_ask_the_original(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    setup(session, api, make_content, five_on_concept_a)
    missed, result = pass_missing_one(api)
    [retake] = result["retakes"]
    asked = [retake["question"]["id"]]

    for _ in range(6):
        answered = answer_retake(api, retake, "b").json()
        asked.append(answered["next_question"]["id"])

    assert missed not in asked
    assert set(asked[:4]) == concept_siblings(missed)  # every sibling before any repeats
    assert all(a != b for a, b in zip(asked, asked[1:], strict=False))
    pending = api.get(f"{QUIZ}/{result['attempt_id']}/retakes").json()
    assert pending["retakes"][0]["question"]["id"] == asked[-1]


def test_after_a_wrong_retake_a_correct_one_completes_the_lesson(learner: TestClient) -> None:
    missed, result = pass_missing_one(learner)
    [retake] = result["retakes"]

    wrong = answer_retake(learner, retake, None).json()  # unanswered counts as wrong
    right = answer_retake(learner, retake, "a").json()

    # A Concept with exactly two Questions asks its one sibling again.
    assert wrong["next_question"]["id"] == retake["question"]["id"] != missed
    assert (wrong["correct"], right["correct"], right["lesson_completed"]) == (False, True, True)
    assert lesson_states(learner)["w01-l01"] == "completed"


def test_retakes_are_asked_from_the_attempts_pinned_version(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    _, result = pass_missing_one(learner)

    def newer(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        own_explanations(syllabus, bank)
        syllabus["version"] = "v2026-02-01"
        for question in bank["questions"]:
            if question["type"] == "multiple_choice":
                question["answer"] = "b"

    changelog = make_changelog(
        "v2026-02-01",
        "v2026-01-01",
        changelog_entry("lesson", "w01-l01", "changed"),
        *(changelog_entry("question", qid, "changed") for qid in sorted(CONCEPT_OF)[:6]),
    )
    import_folder(
        session,
        make_content(
            newer, extra_banks={"w01-l02": make_bank("w01-l02", "second")}, changelog=changelog
        ),
    )

    answered = answer_retake(learner, result["retakes"][0], "a").json()

    assert (answered["correct"], answered["lesson_completed"]) == (True, True)


# --- Below the Pass Mark: a fresh quiz -------------------------------------------------------


def test_below_the_pass_mark_there_are_no_retakes_and_the_fresh_quiz_avoids_old_questions(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    setup(session, api, make_content, ten_multiple_choice)
    first = start(api)
    first_ids = {q["id"] for q in first["questions"]}
    multiple_choice = {question_number(n) for n in [*range(1, 7), *range(9, 13)]}

    result = submit(api, first, answer_all(first, wrong=2)).json()

    assert (result["passed"], result["next_step"], result["lesson_completed"]) == (
        False,
        "fresh_quiz",
        False,
    )
    assert result["retakes"] == []
    assert len(result["missed"]) == 2
    fresh = start(api)
    fresh_ids = {q["id"] for q in fresh["questions"]}
    assert fresh["attempt_id"] != first["attempt_id"]
    assert multiple_choice - first_ids <= fresh_ids  # all four unused Questions
    assert len(fresh_ids & first_ids) == 2  # and only the two repeats it can't avoid


def test_a_fresh_quiz_repeats_questions_only_when_the_bank_is_too_small(
    learner: TestClient,
) -> None:
    first = start(learner)
    submit(learner, first, answer_all(first, wrong=2))

    fresh = start(learner)

    # Only six multiple-choice Questions in this bank, so the fresh quiz has to reuse them.
    assert {q["id"] for q in fresh["questions"]} == {q["id"] for q in first["questions"]}


# --- Missed Questions for the Daily Review ---------------------------------------------------


def test_every_missed_question_is_recorded_for_the_daily_review(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    setup(session, api, make_content, five_on_concept_a)
    missed, result = pass_missing_one(api)
    [retake] = result["retakes"]
    wrong_sibling = retake["question"]["id"]
    answered = answer_retake(api, retake, "b").json()
    answer_retake(api, {"id": retake["id"]}, "a")

    missed_ids = quizzes.missed_question_ids(session, learner_id(session), "mini-stack")

    # In the order first missed; the sibling answered correctly at the end isn't one.
    assert missed_ids == [missed, wrong_sibling]
    assert answered["next_question"]["id"] not in missed_ids
    [first, second] = quizzes.missed_questions(session, learner_id(session), "mini-stack")
    assert (first.question_id, first.syllabus_version) == (missed, "v2026-01-01")
    assert second.first_missed_at >= first.first_missed_at


def test_missed_questions_are_kept_per_learner(
    session: Session, learner: TestClient, admin: TestClient, signed_in: ClientFactory
) -> None:
    admin.post("/invitations", json={"email": "other@example.com"}).raise_for_status()
    onboard(signed_in("other@example.com"))
    pass_missing_one(learner)

    assert quizzes.missed_question_ids(session, learner_id(session), "mini-stack") != []
    other = learner_id(session, "other@example.com")
    assert quizzes.missed_question_ids(session, other, "mini-stack") == []


# --- Refusals --------------------------------------------------------------------------------


def test_a_retake_already_answered_correctly_is_refused(learner: TestClient) -> None:
    _, result = pass_missing_one(learner)
    [retake] = result["retakes"]
    answer_retake(learner, retake, "a")

    assert code(answer_retake(learner, retake, "a")) == (409, "retake_done")


def test_a_retake_answer_that_is_not_one_of_the_choices_is_rejected(learner: TestClient) -> None:
    _, result = pass_missing_one(learner)

    assert code(answer_retake(learner, result["retakes"][0], "z")) == (422, "not_a_choice")


def test_another_learners_retakes_are_not_found(
    learner: TestClient, admin: TestClient, signed_in: ClientFactory
) -> None:
    admin.post("/invitations", json={"email": "other@example.com"}).raise_for_status()
    other = signed_in("other@example.com")
    onboard(other)
    _, result = pass_missing_one(learner)

    assert answer_retake(other, result["retakes"][0], "a").status_code == 404
    assert other.get(f"{QUIZ}/{result['attempt_id']}/retakes").status_code == 404
    assert answer_retake(learner, {"id": "not-a-uuid"}, "a").status_code == 404


def test_the_learners_answers_to_retakes_are_recorded(
    session: Session, learner: TestClient
) -> None:
    _, result = pass_missing_one(learner)
    [retake] = result["retakes"]
    answer_retake(learner, retake, "b")

    recorded = quizzes.recorded_answers(session, learner_id(session, LEARNER_EMAIL), "mini-stack")
    [retake_answer] = [a for a in recorded if a.context == "retake"]
    assert (retake_answer.question_id, retake_answer.response, retake_answer.correct) == (
        retake["question"]["id"],
        "b",
        False,
    )
    assert str(retake_answer.retake_id) == retake["id"]
