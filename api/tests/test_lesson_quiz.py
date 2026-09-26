"""Taking a Lesson Quiz over the API: starting it, submitting answers, and what a pass unlocks
(#6). The rules themselves are tested in test_lesson_quiz_rules.py."""

import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import quizzes
from app.content.importer import import_folder
from app.models import Learner
from tests.conftest import (
    LEARNER_EMAIL,
    ClientFactory,
    ContentFactory,
    changelog_entry,
    make_bank,
    make_changelog,
    onboard,
)

QUIZ = "/stacks/mini-stack/lessons/w01-l01/quiz"

# The mini Stack's bank for w01-l01 has six multiple-choice Questions, q01 to q06, each with
# choices "a" (correct) and "b", and two written ones, q07 and q08.
MULTIPLE_CHOICE = {f"w01-l01-q{n:02}" for n in range(1, 7)}


def no_second_bank(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    """Leave the mini Stack as it is: w01-l02 has no Question Bank."""


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory
) -> Iterator[TestClient]:
    """A new Learner onboarded onto the mini Stack, where both Lessons have a Question Bank."""
    import_folder(session, make_content(extra_banks={"w01-l02": make_bank("w01-l02", "second")}))
    onboard(api)
    yield api


def start(client: TestClient, url: str = QUIZ) -> dict[str, Any]:
    response = client.post(url)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def submit(
    client: TestClient, quiz: dict[str, Any], answers: dict[str, str | None], url: str = QUIZ
) -> Response:
    return client.post(f"{url}/{quiz['attempt_id']}/answers", json={"answers": answers})


def answer_all(quiz: dict[str, Any], *, wrong: int = 0) -> dict[str, str | None]:
    """Answer every Question: the first `wrong` of them wrongly, the rest correctly."""
    ids = [q["id"] for q in quiz["questions"]]
    return {qid: ("b" if i < wrong else "a") for i, qid in enumerate(ids)}


def lesson_states(client: TestClient) -> dict[str, str]:
    weeks = client.get("/stacks/mini-stack").json()["weeks"]
    return {lesson["id"]: lesson["state"] for week in weeks for lesson in week["lessons"]}


def code(response: Response) -> tuple[int, str]:
    return response.status_code, response.json()["detail"]["code"]


def learner_id(session: Session, email: str = LEARNER_EMAIL) -> int:
    return session.scalars(select(Learner.id).where(Learner.email == email)).one()


# --- Starting --------------------------------------------------------------------------------


def test_the_quiz_draws_six_multiple_choice_questions_from_the_lessons_bank(
    learner: TestClient,
) -> None:
    quiz = start(learner)

    assert {q["id"] for q in quiz["questions"]} == MULTIPLE_CHOICE
    assert {q["type"] for q in quiz["questions"]} == {"multiple_choice"}
    first = next(q for q in quiz["questions"] if q["id"] == "w01-l01-q01")
    assert first == {
        "id": "w01-l01-q01",
        "type": "multiple_choice",
        "prompt": "Question 1?",
        "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
    }
    assert (quiz["lesson_id"], quiz["version"], quiz["pass_mark"]) == ("w01-l01", "v2026-01-01", 80)


def test_the_correct_answers_are_never_sent_before_submission(learner: TestClient) -> None:
    response = learner.post(QUIZ)

    assert keys(response.json()).isdisjoint({"answer", "explanation", "model_answer"})
    assert "Because." not in response.text  # every Explanation in the bank


def keys(value: Any) -> set[str]:
    """Every key anywhere in a JSON value."""
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys(v)}
    return set()


def test_starting_again_before_submitting_resumes_the_same_quiz(
    learner: TestClient, signed_in: ClientFactory
) -> None:
    first = start(learner)

    assert start(signed_in(LEARNER_EMAIL)) == first


def test_a_lesson_without_a_question_bank_has_no_quiz_yet(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content(no_second_bank))
    onboard(api)
    quiz = start(api)
    submit(api, quiz, answer_all(quiz))

    response = api.post("/stacks/mini-stack/lessons/w01-l02/quiz")

    assert code(response) == (409, "quiz_unavailable")


# --- Scoring and unlocking -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("wrong", "correct", "percent", "passed"),
    [(0, 6, 100, True), (1, 5, 83, True), (2, 4, 67, False)],
)
def test_the_server_scores_the_quiz_against_the_pass_mark(
    learner: TestClient, wrong: int, correct: int, percent: int, passed: bool
) -> None:
    quiz = start(learner)
    answers = answer_all(quiz, wrong=wrong)

    result = submit(learner, quiz, answers).json()

    assert (result["correct"], result["total"], result["percent"], result["passed"]) == (
        correct,
        6,
        percent,
        passed,
    )
    assert result["questions"] == [
        {"id": qid, "correct": answer == "a"} for qid, answer in answers.items()
    ]


def test_passing_completes_the_lesson_and_unlocks_the_next_on_the_week_map(
    learner: TestClient,
) -> None:
    quiz = start(learner)

    submit(learner, quiz, answer_all(quiz, wrong=1))

    assert lesson_states(learner) == {"w01-l01": "completed", "w01-l02": "unlocked"}
    assert learner.post("/stacks/mini-stack/lessons/w01-l02/quiz").status_code == 200


def test_failing_leaves_the_lesson_unlocked_and_the_next_quiz_is_a_fresh_one(
    learner: TestClient,
) -> None:
    quiz = start(learner)

    submit(learner, quiz, answer_all(quiz, wrong=2))

    assert lesson_states(learner) == {"w01-l01": "unlocked", "w01-l02": "locked"}
    assert start(learner)["attempt_id"] != quiz["attempt_id"]


def test_an_unanswered_question_counts_as_missed(learner: TestClient) -> None:
    quiz = start(learner)
    answers = answer_all(quiz)
    skipped = list(answers)[:2]
    answers[skipped[0]] = None
    del answers[skipped[1]]

    result = submit(learner, quiz, answers).json()

    assert (result["correct"], result["passed"]) == (4, False)
    assert {q["id"] for q in result["questions"] if not q["correct"]} == set(skipped)


# --- Recording answers -----------------------------------------------------------------------


def test_every_answer_is_recorded_against_the_learner_the_question_and_its_version(
    session: Session, learner: TestClient
) -> None:
    quiz = start(learner)
    answers = answer_all(quiz, wrong=1)
    missed = list(answers)[0]
    unanswered = list(answers)[1]
    del answers[unanswered]

    submit(learner, quiz, answers)

    recorded = quizzes.recorded_answers(session, learner_id(session), "mini-stack")
    assert sorted(
        (
            a.question_id,
            a.syllabus_version,
            a.context,
            str(a.lesson_quiz_attempt_id),
            a.response,
            a.correct,
        )
        for a in recorded
    ) == sorted(
        [
            (qid, "v2026-01-01", "lesson_quiz", quiz["attempt_id"], answer, answer == "a")
            for qid, answer in answers.items()
        ]
        + [(unanswered, "v2026-01-01", "lesson_quiz", quiz["attempt_id"], None, False)]
    )
    assert missed in {a.question_id for a in recorded if a.correct is False}


def test_answers_are_kept_per_learner(
    session: Session, learner: TestClient, admin: TestClient, signed_in: ClientFactory
) -> None:
    admin.post("/invitations", json={"email": "other@example.com"}).raise_for_status()
    other = signed_in("other@example.com")
    onboard(other)
    quiz = start(learner)
    submit(learner, quiz, answer_all(quiz))

    assert (
        quizzes.recorded_answers(session, learner_id(session, "other@example.com"), "mini-stack")
        == []
    )


# --- Refusals --------------------------------------------------------------------------------


def test_a_quiz_cannot_be_submitted_twice(session: Session, learner: TestClient) -> None:
    quiz = start(learner)
    submit(learner, quiz, answer_all(quiz, wrong=2))

    response = submit(learner, quiz, answer_all(quiz))

    assert code(response) == (409, "quiz_submitted")
    assert lesson_states(learner)["w01-l01"] == "unlocked"
    assert len(quizzes.recorded_answers(session, learner_id(session), "mini-stack")) == 6


def test_an_answer_to_a_question_not_in_the_quiz_is_rejected(
    session: Session, learner: TestClient
) -> None:
    quiz = start(learner)
    answers = {**answer_all(quiz), "w01-l01-q07": "a"}

    response = submit(learner, quiz, answers)

    assert code(response) == (422, "question_not_in_quiz")
    assert quizzes.recorded_answers(session, learner_id(session), "mini-stack") == []
    assert submit(learner, quiz, answer_all(quiz)).status_code == 200


def test_an_answer_that_is_not_one_of_the_choices_is_rejected(learner: TestClient) -> None:
    quiz = start(learner)
    answers = answer_all(quiz)
    answers[next(iter(answers))] = "z"

    assert code(submit(learner, quiz, answers)) == (422, "not_a_choice")


def test_another_learners_quiz_cannot_be_submitted(
    learner: TestClient, admin: TestClient, signed_in: ClientFactory
) -> None:
    admin.post("/invitations", json={"email": "other@example.com"}).raise_for_status()
    other = signed_in("other@example.com")
    onboard(other)
    quiz = start(learner)

    assert submit(other, quiz, answer_all(quiz)).status_code == 404


def test_an_unknown_quiz_is_not_found(learner: TestClient) -> None:
    fake = {"attempt_id": "00000000-0000-0000-0000-000000000000"}
    assert submit(learner, fake, {}).status_code == 404
    assert submit(learner, {"attempt_id": "not-a-uuid"}, {}).status_code == 404


# --- A new Syllabus version (#13) ------------------------------------------------------------


def test_a_quiz_in_progress_finishes_on_the_version_it_started_on(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    quiz = start(learner)

    def newer(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["version"] = "v2026-02-01"
        for question in bank["questions"]:
            if question["type"] == "multiple_choice":
                question["answer"] = "b"

    changelog = make_changelog(
        "v2026-02-01",
        "v2026-01-01",
        changelog_entry("lesson", "w01-l01", "changed"),
        *(changelog_entry("question", qid, "changed") for qid in sorted(MULTIPLE_CHOICE)),
    )
    import_folder(
        session,
        make_content(
            newer,
            extra_banks={"w01-l02": make_bank("w01-l02", "second")},
            changelog=changelog,
        ),
    )
    assert learner.get("/stacks/mini-stack").json()["version"] == "v2026-02-01"

    result = submit(learner, quiz, answer_all(quiz)).json()

    assert (result["correct"], result["passed"]) == (6, True)
    recorded = quizzes.recorded_answers(session, learner_id(session), "mini-stack")
    assert {a.syllabus_version for a in recorded} == {"v2026-01-01"}


def test_the_quiz_start_response_is_plain_json(learner: TestClient) -> None:
    # Guards against leaking internal row keys: only permanent IDs and a random attempt ID.
    quiz = start(learner)
    assert set(quiz) == {"attempt_id", "lesson_id", "version", "pass_mark", "questions"}
    assert "pk" not in json.dumps(quiz)
