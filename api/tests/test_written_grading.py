"""Grading written answers in a Lesson Quiz over the API (#7), with the fake grader from
conftest.py in place of Claude: pass/fail with feedback, and resubmitting after a grading
failure without penalty. The grader itself is tested in test_grading.py."""

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import grading, quizzes
from app.content.importer import import_folder
from app.deps import get_grader
from tests.conftest import ContentFactory, FakeGrader, onboard
from tests.test_lesson_quiz import (
    RIGHT,
    WRITTEN,
    answer_all,
    code,
    learner_id,
    lesson_states,
    start,
    submit,
)


@pytest.fixture
def learner(session: Session, api: TestClient, make_content: ContentFactory) -> TestClient:
    """A new Learner onboarded onto the mini Stack."""
    import_folder(session, make_content())
    onboard(api)
    return api


def recorded(session: Session) -> list[Any]:
    return quizzes.recorded_answers(session, learner_id(session), "mini-stack")


def test_written_answers_are_graded_and_their_feedback_is_returned_and_recorded(
    session: Session, learner: TestClient, grader: FakeGrader
) -> None:
    quiz = start(learner)
    answers = answer_all(quiz)
    answers[WRITTEN[1]] = "I don't know."

    result = submit(learner, quiz, answers).json()

    by_id = {q["id"]: q for q in result["questions"]}
    assert by_id[WRITTEN[0]] == {
        "id": WRITTEN[0],
        "correct": True,
        "feedback": "Covers every key point.",
    }
    assert by_id[WRITTEN[1]] == {"id": WRITTEN[1], "correct": False, "feedback": "Missing: one."}
    assert {by_id[q["id"]]["feedback"] for q in quiz["questions"][:4]} == {None}
    assert (result["correct"], result["passed"]) == (5, True)
    rows = {a.question_id: a for a in recorded(session)}
    assert (rows[WRITTEN[1]].response, rows[WRITTEN[1]].correct) == ("I don't know.", False)
    assert rows[WRITTEN[1]].feedback == "Missing: one."


def test_the_grader_gets_the_question_its_model_answer_and_the_learners_answer(
    learner: TestClient, grader: FakeGrader
) -> None:
    quiz = start(learner)
    answers = answer_all(quiz)
    answers["w01-l01-q07"] = "My own right words."

    submit(learner, quiz, answers)

    assert (
        "Explain 7.",
        {"summary": "S", "key_points": ["one", "two"]},
        "My own right words.",
    ) in grader.calls
    assert len(grader.calls) == 2


def test_an_unanswered_or_blank_written_answer_is_missed_without_grading(
    learner: TestClient, grader: FakeGrader
) -> None:
    quiz = start(learner)
    answers = answer_all(quiz)
    answers[WRITTEN[0]] = "   \n"
    del answers[WRITTEN[1]]

    result = submit(learner, quiz, answers).json()

    assert grader.calls == []
    assert [q["correct"] for q in result["questions"][4:]] == [False, False]
    assert (result["correct"], result["passed"]) == (4, False)


def test_when_grading_fails_nothing_counts_and_the_learner_can_resubmit(
    session: Session, learner: TestClient, grader: FakeGrader
) -> None:
    quiz = start(learner)
    grader.failing = True

    response = submit(learner, quiz, answer_all(quiz))

    assert code(response) == (503, "grading_failed")
    assert recorded(session) == []
    assert lesson_states(learner)["w01-l01"] == "unlocked"
    assert start(learner) == quiz  # the attempt is still open

    grader.failing = False
    result = submit(learner, quiz, answer_all(quiz)).json()

    assert (result["correct"], result["total"], result["passed"]) == (6, 6, True)
    assert len(recorded(session)) == 6
    assert lesson_states(learner)["w01-l01"] == "completed"


def test_a_bad_choice_is_refused_before_any_grading(
    learner: TestClient, grader: FakeGrader
) -> None:
    quiz = start(learner)
    answers = answer_all(quiz)
    answers[quiz["questions"][0]["id"]] = "z"

    assert code(submit(learner, quiz, answers)) == (422, "not_a_choice")
    assert grader.calls == []


def test_an_overlong_written_answer_is_refused_before_any_grading(
    session: Session, learner: TestClient, grader: FakeGrader
) -> None:
    quiz = start(learner)
    assert quiz["max_answer_chars"] == grading.MAX_ANSWER_CHARS
    answers = answer_all(quiz)
    answers[WRITTEN[0]] = RIGHT + "x" * grading.MAX_ANSWER_CHARS

    assert code(submit(learner, quiz, answers)) == (422, "answer_too_long")
    assert grader.calls == []
    assert recorded(session) == []


def test_without_an_api_key_grading_fails_cleanly_and_can_be_retried(
    app: FastAPI, learner: TestClient
) -> None:
    del app.dependency_overrides[get_grader]
    app.state.grader = grading.grader_from_config("")
    quiz = start(learner)

    assert code(submit(learner, quiz, answer_all(quiz))) == (503, "grading_failed")
    assert start(learner)["attempt_id"] == quiz["attempt_id"]
    # With the written Questions left unanswered there is nothing to grade.
    without_written = {qid: a for qid, a in answer_all(quiz).items() if qid not in WRITTEN}
    assert submit(learner, quiz, without_written).json()["correct"] == 4
