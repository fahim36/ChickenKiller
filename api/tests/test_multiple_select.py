"""Multiple-select Questions over the API (ADR-0008): select all that apply, correct only when
the choices ticked are exactly the correct ones. They take the written Questions' place: a
Lesson Quiz asks four multiple choice then two multiple select, and a Daily Challenge two
multiple choice then one multiple select. An answer is the list of choice IDs ticked.

The mini Stack here is `MS_BANK`: w01-l01's q01 to q06 are multiple choice ("a" is right) and
q07 and q08 multiple select, both with choices a to d and "a" and "c" right."""

import copy
from datetime import UTC, date, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import quizzes
from app.content.importer import import_folder
from app.models import Answer, Question
from tests.conftest import (
    CHALLENGE_MIX,
    MS_BANK,
    ContentFactory,
    FakeClock,
    FakeGrader,
    challenge,
    complete_lessons,
    onboard,
    write_challenges,
)
from tests.test_lesson_quiz import QUIZ, learner_id, start, submit

MC1, MC2, SELECT = CHALLENGE_MIX
MULTIPLE_SELECT = ["w01-l01-q07", "w01-l01-q08"]
RIGHT_TICKS = ["c", "a"]
MORNING = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


def multiple_select(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    bank.update(copy.deepcopy(MS_BANK))


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> TestClient:
    """A Learner on the mini Stack with Daily Challenge #1 (1 Jan) to play, at 10:00 UTC."""
    clock.set(MORNING)
    folder = make_content(multiple_select)
    write_challenges(folder.parent, challenge(1))
    import_folder(session, folder, today=date(2026, 1, 1))
    onboard(api)
    return api


def test_the_import_stores_every_correct_choice(session: Session, learner: TestClient) -> None:
    question = session.scalars(select(Question).where(Question.id == SELECT)).one()

    assert (question.type, question.answers, question.answer) == (
        "multiple_select",
        ["a", "c"],
        None,
    )
    assert [c["id"] for c in question.choices or []] == ["a", "b", "c", "d"]


# --- The Lesson Quiz ---------------------------------------------------------------------------


def test_the_quiz_asks_four_multiple_choice_then_two_multiple_select(learner: TestClient) -> None:
    quiz = start(learner)

    assert [q["type"] for q in quiz["questions"]] == ["multiple_choice"] * 4 + [
        "multiple_select"
    ] * 2
    assert sorted(q["id"] for q in quiz["questions"][4:]) == MULTIPLE_SELECT
    assert {"id": "a", "text": "Right one"} in quiz["questions"][4]["choices"]
    assert "answers" not in quiz["questions"][4]


def test_choices_are_shuffled_the_same_way_every_time(learner: TestClient) -> None:
    first = {q["id"]: q["choices"] for q in start(learner)["questions"]}
    again = {q["id"]: q["choices"] for q in start(learner)["questions"]}

    for question_id in first.keys() & again.keys():
        assert first[question_id] == again[question_id]
    assert any(
        [c["id"] for c in choices] != sorted(c["id"] for c in choices) for choices in first.values()
    )


def test_ticking_exactly_the_right_choices_passes_and_anything_else_is_missed(
    session: Session, learner: TestClient
) -> None:
    quiz = start(learner)
    first, second = (q["id"] for q in quiz["questions"][4:])
    answers: dict[str, Any] = {q["id"]: "a" for q in quiz["questions"][:4]}
    answers |= {first: RIGHT_TICKS, second: ["a"]}  # one right one missed: no partial credit

    result = submit(learner, quiz, answers).json()

    assert (result["correct"], result["total"], result["passed"]) == (5, 6, True)
    [missed] = result["missed"]
    assert (missed["id"], missed["type"], missed["selected"], missed["answers"]) == (
        second,
        "multiple_select",
        ["a"],
        ["a", "c"],
    )
    assert (missed["response"], missed["answer"], missed["explanation"]) == ("a", None, "Because.")
    assert missed["sources"][0]["url"] == "https://example.com/docs/page-1"
    recorded = {
        a.question_id: a.response
        for a in quizzes.recorded_answers(session, learner_id(session), "mini-stack")
    }
    assert (recorded[first], recorded[second]) == ("a,c", "a")


def test_a_tick_that_is_not_a_choice_records_nothing(session: Session, learner: TestClient) -> None:
    quiz = start(learner)
    select_id = quiz["questions"][4]["id"]

    response = submit(learner, quiz, {select_id: ["a", "z"]})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "not_a_choice"
    assert quizzes.recorded_answers(session, learner_id(session), "mini-stack") == []


def test_no_ticks_is_unanswered(learner: TestClient) -> None:
    quiz = start(learner)
    answers: dict[str, Any] = {q["id"]: "a" for q in quiz["questions"][:4]}
    answers |= {quiz["questions"][4]["id"]: [], quiz["questions"][5]["id"]: RIGHT_TICKS}

    result = submit(learner, quiz, answers).json()

    [missed] = result["missed"]
    assert (missed["response"], missed["selected"]) == (None, [])


def test_a_retake_can_ask_a_multiple_select_sibling(learner: TestClient) -> None:
    quiz = start(learner)
    first, second = (q["id"] for q in quiz["questions"][4:])
    answers: dict[str, Any] = {q["id"]: "a" for q in quiz["questions"][:4]}
    answers |= {first: RIGHT_TICKS, second: ["b", "d"]}

    result = submit(learner, quiz, answers).json()

    [retake] = result["retakes"]
    assert retake["question"]["id"] == first  # the only sibling on its Concept
    answered = learner.post(
        f"{QUIZ.removesuffix('/quiz')}/retakes/{retake['id']}/answers",
        json={"answer": RIGHT_TICKS},
    ).json()
    assert (answered["correct"], answered["lesson_completed"]) == (True, True)


# --- The Daily Challenge -----------------------------------------------------------------------


def play(client: TestClient, question_id: str, given: Any) -> dict[str, Any]:
    response = client.post(
        "/stacks/mini-stack/challenges/1/answers",
        json={"question_id": question_id, "answer": given},
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_the_challenge_ends_on_its_multiple_select_question(learner: TestClient) -> None:
    body = learner.get("/stacks/mini-stack/challenges/today").json()

    questions = body["challenge"]["questions"]
    assert [q["type"] for q in questions] == [
        "multiple_choice",
        "multiple_choice",
        "multiple_select",
    ]
    assert questions[2]["answered"] is None
    assert len(questions[2]["choices"]) == 4


def test_a_challenge_multiple_select_answer_shows_the_ticks_and_the_correct_set(
    learner: TestClient,
) -> None:
    play(learner, MC1, "a")
    play(learner, MC2, "a")
    result = play(learner, SELECT, ["a", "b", "c"])

    assert (result["counted"], result["outcome"]) == (True, "wrong")
    question = result["question"]
    assert (question["selected"], question["answers"]) == (["a", "b", "c"], ["a", "c"])
    assert question["explanation"] == "Because."
    assert result["challenge"]["result_card"].endswith("2/3 ✅✅❌")


def test_a_challenge_multiple_select_question_is_never_ungraded(
    learner: TestClient, grader: FakeGrader
) -> None:
    """It is marked without a grading call, so a failing grader changes nothing: the Result
    Card can't show ⬜ for it."""
    grader.failing = True
    play(learner, MC1, "a")
    play(learner, MC2, "b")
    result = play(learner, SELECT, RIGHT_TICKS)

    assert result["outcome"] == "correct"
    assert result["challenge"]["result_card"].endswith("2/3 ✅❌✅")
    assert "⬜" not in result["challenge"]["result_card"]
    assert grader.calls == []


def test_a_challenge_replay_of_a_multiple_select_question_changes_nothing(
    session: Session, learner: TestClient
) -> None:
    play(learner, MC1, "a")
    play(learner, MC2, "a")
    play(learner, SELECT, ["a"])

    again = play(learner, SELECT, RIGHT_TICKS)

    assert (again["counted"], again["outcome"]) == (False, "correct")
    session.expire_all()
    recorded = session.scalars(
        select(Answer.response).where(
            Answer.context == "daily_challenge", Answer.question_id == SELECT
        )
    ).all()
    assert recorded == ["a"]
    assert SELECT in quizzes.missed_question_ids(session, learner_id(session), "mini-stack")


# --- Review ------------------------------------------------------------------------------------


def test_review_takes_a_list_of_ticks(session: Session, learner: TestClient) -> None:
    complete_lessons(session, "w01-l01")

    response = learner.post(
        "/review/answers",
        json={"stack_id": "mini-stack", "question_id": SELECT, "answer": RIGHT_TICKS},
    )

    assert response.status_code == 200, response.text
    assert response.json()["correct"] is True
    assert response.json()["question"]["selected"] == ["a", "c"]
