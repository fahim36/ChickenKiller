"""The Daily Review over the API (#9): Round 1 opening on the first use of the day, in the
Learner's time zone; its Questions; answering them one at a time; and a Pending Review Round
locking the Unlocked Lesson until it's finished. The clock is the test's (`clock`, conftest.py),
so time moves only when a test moves it. The rules themselves are tested in
test_review_rules.py.

The mini Stack's Lessons each have a bank of eight Questions: six multiple choice (choice "a"
is right) and two written (the fake grader passes an answer saying "right")."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from tests.conftest import (
    ContentFactory,
    FakeClock,
    FakeGrader,
    complete_lessons,
    make_bank,
    onboard,
)
from tests.test_lesson_quiz import (
    RIGHT,
    WRONG,
    answer_all,
    code,
    keys,
    lesson_states,
    start,
    submit,
)

REVIEW = "/stacks/mini-stack/review"
SECOND_QUIZ = "/stacks/mini-stack/lessons/w01-l02/quiz"
FIRST_BANK = {f"w01-l01-q{n:02}" for n in range(1, 9)}
FIRST_WRITTEN = {"w01-l01-q07", "w01-l01-q08"}

# 10:00 in Dhaka (UTC+6) on 26 September.
MORNING = datetime(2026, 9, 26, 4, 0, tzinfo=UTC)


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> TestClient:
    """A Learner in Asia/Dhaka on the mini Stack, whose first Lesson (w01-l01) is a Completed
    Lesson, and who hasn't used the app yet today. It is 10:00 in Dhaka."""
    clock.set(MORNING)
    import_folder(session, make_content(extra_banks={"w01-l02": make_bank("w01-l02", "second")}))
    onboard(api, time_zone="Asia/Dhaka")
    complete_lessons(session, "w01-l01")
    return api


def daily_review(client: TestClient) -> dict[str, Any]:
    response = client.get(REVIEW)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def current_round(client: TestClient) -> dict[str, Any]:
    current: dict[str, Any] | None = daily_review(client)["current"]
    assert current is not None, "no Review Round is open"
    return current


def answer(
    client: TestClient, round_: dict[str, Any], question_id: str, response: str | None
) -> Response:
    return client.post(
        f"{REVIEW}/rounds/{round_['id']}/answers",
        json={"question_id": question_id, "answer": response},
    )


def right_answer(question: dict[str, Any]) -> str:
    return RIGHT if question["type"] == "written" else "a"


def wrong_answer(question: dict[str, Any]) -> str:
    return WRONG if question["type"] == "written" else "b"


def finish(client: TestClient, round_: dict[str, Any]) -> dict[str, Any]:
    """Answer every remaining Question of the round correctly; the last answer's result."""
    result: dict[str, Any] = {}
    for question in round_["remaining"]:
        response = answer(client, round_, question["id"], right_answer(question))
        assert response.status_code == 200, response.text
        result = response.json()
    return result


# --- Opening Round 1 ---------------------------------------------------------------------------


def test_the_first_use_of_the_day_opens_round_1_with_the_completed_lessons_questions(
    learner: TestClient,
) -> None:
    learner.get("/me")

    review = daily_review(learner)

    assert review["day"] == "2026-09-26"
    [summary] = review["rounds"]
    assert summary == {
        "id": summary["id"],
        "number": 1,
        "state": "optional",
        "opened_at": "2026-09-26T04:00:00Z",
        "pending_at": "2026-09-26T06:00:00Z",
        "finished_at": None,
        "answered": 0,
        "total": 8,
    }
    current = review["current"]
    assert current["id"] == summary["id"]
    assert {q["id"] for q in current["remaining"]} == FIRST_BANK
    assert current["results"] == []
    assert current["max_answer_chars"] == 4000


def test_a_round_s_questions_come_without_their_answers(learner: TestClient) -> None:
    response = learner.get(REVIEW)

    assert keys(response.json()["current"]["remaining"]).isdisjoint(
        {"answer", "explanation", "model_answer", "key_points", "summary"}
    )
    assert "Because." not in response.text


def test_using_the_app_again_the_same_day_opens_no_other_round(
    learner: TestClient, clock: FakeClock
) -> None:
    first = daily_review(learner)["rounds"]
    learner.get("/stacks/mini-stack")
    clock.advance(hours=13, minutes=59)  # 23:59 in Dhaka

    rounds = daily_review(learner)["rounds"]

    assert [r["id"] for r in rounds] == [first[0]["id"]]


def test_the_next_day_starts_at_midnight_in_dhaka_with_a_new_round_1(
    learner: TestClient, clock: FakeClock
) -> None:
    clock.set(datetime(2026, 9, 26, 17, 59, 59, tzinfo=UTC))  # 23:59:59 in Dhaka
    yesterday = daily_review(learner)
    clock.advance(seconds=1)  # midnight in Dhaka, still the 26th in UTC

    today = daily_review(learner)

    assert (yesterday["day"], today["day"]) == ("2026-09-26", "2026-09-27")
    [round_1] = today["rounds"]
    assert round_1["number"] == 1
    assert round_1["id"] != yesterday["rounds"][0]["id"]
    assert round_1["opened_at"] == "2026-09-26T18:00:00Z"


def test_a_learner_with_no_completed_lesson_gets_no_daily_review(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    clock.set(MORNING)
    import_folder(session, make_content())
    onboard(api, time_zone="Asia/Dhaka")

    review = daily_review(api)

    assert (review["rounds"], review["current"]) == ([], None)
    assert api.get("/stacks/mini-stack").json()["daily_review"] is None
    assert api.post("/stacks/mini-stack/lessons/w01-l01/quiz").status_code == 200


def test_a_lesson_completed_during_the_day_brings_a_daily_review_the_next_day(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    """Round 1 opens on the day's first use: a Learner with nothing to review then owes
    nothing that day, even after completing a Lesson."""
    clock.set(MORNING)
    import_folder(session, make_content())
    onboard(api, time_zone="Asia/Dhaka")
    quiz = start(api, "/stacks/mini-stack/lessons/w01-l01/quiz")
    submit(api, quiz, answer_all(quiz), "/stacks/mini-stack/lessons/w01-l01/quiz")

    assert daily_review(api)["rounds"] == []
    clock.advance(days=1)
    assert [r["number"] for r in daily_review(api)["rounds"]] == [1]


def test_missed_questions_lead_the_round_ahead_of_the_completed_lessons_questions(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    clock.set(MORNING)
    import_folder(session, make_content())
    onboard(api, time_zone="Asia/Dhaka")
    url = "/stacks/mini-stack/lessons/w01-l01/quiz"
    quiz = start(api, url)
    missed = quiz["questions"][0]["id"]
    result = submit(api, quiz, answer_all(quiz, wrong=1), url).json()
    [retake] = result["retakes"]
    retake_url = f"/stacks/mini-stack/lessons/w01-l01/retakes/{retake['id']}/answers"
    assert api.post(retake_url, json={"answer": "a"}).json()["lesson_completed"] is True
    clock.advance(days=1)

    remaining = current_round(api)["remaining"]

    assert remaining[0]["id"] == missed
    assert {q["id"] for q in remaining} == FIRST_BANK


# --- Answering a round -------------------------------------------------------------------------


def test_a_right_answer_is_marked_correct(learner: TestClient) -> None:
    round_ = current_round(learner)
    question = next(q for q in round_["remaining"] if q["type"] == "multiple_choice")

    result = answer(learner, round_, question["id"], "a").json()

    assert result["correct"] is True
    assert result["question"]["id"] == question["id"]
    assert (result["round"]["answered"], result["round"]["state"]) == (1, "optional")
    after = current_round(learner)
    assert question["id"] not in {q["id"] for q in after["remaining"]}
    assert [r["question"]["id"] for r in after["results"]] == [question["id"]]


def test_a_wrong_answer_shows_its_explanation_and_correct_answer(learner: TestClient) -> None:
    round_ = current_round(learner)
    question = next(q for q in round_["remaining"] if q["type"] == "multiple_choice")

    result = answer(learner, round_, question["id"], "b").json()

    assert result["correct"] is False
    assert result["question"] == {
        "id": question["id"],
        "type": "multiple_choice",
        "prompt": question["prompt"],
        "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
        "response": "b",
        "feedback": None,
        "answer": "a",
        "model_answer": None,
        "explanation": "Because.",
        "materials": [
            {
                "id": "mat-docs",
                "title": "Some docs",
                "url": "https://example.com/docs",
                "type": "docs",
            }
        ],
    }


def test_a_written_answer_is_graded_and_a_miss_shows_the_model_answer_and_feedback(
    learner: TestClient,
) -> None:
    round_ = current_round(learner)
    first, second = (q["id"] for q in round_["remaining"] if q["type"] == "written")

    missed = answer(learner, round_, first, WRONG).json()
    passed = answer(learner, round_, second, RIGHT).json()

    assert missed["correct"] is False
    assert missed["question"]["feedback"] == "Missing: one."
    assert missed["question"]["model_answer"] == {"summary": "S", "key_points": ["one", "two"]}
    assert missed["question"]["explanation"] == "Because."
    assert (passed["correct"], passed["question"]["feedback"]) == (True, "Covers every key point.")


def test_when_grading_fails_nothing_is_recorded_and_the_learner_answers_again(
    learner: TestClient, grader: FakeGrader
) -> None:
    round_ = current_round(learner)
    written = next(q["id"] for q in round_["remaining"] if q["type"] == "written")
    grader.failing = True

    failed = answer(learner, round_, written, RIGHT)
    grader.failing = False
    retried = answer(learner, round_, written, RIGHT)

    assert code(failed) == (503, "grading_failed")
    assert (retried.status_code, retried.json()["correct"]) == (200, True)


def test_each_question_is_answered_once(learner: TestClient) -> None:
    round_ = current_round(learner)
    question = round_["remaining"][0]["id"]
    answer(learner, round_, question, "b")

    assert code(answer(learner, round_, question, "a")) == (409, "question_answered")
    assert code(answer(learner, round_, "w01-l02-q01", "a")) == (422, "question_not_in_round")


def test_a_wrong_answer_in_a_round_is_a_missed_question_the_next_day(
    learner: TestClient, clock: FakeClock
) -> None:
    round_ = current_round(learner)
    last = round_["remaining"][-1]
    answer(learner, round_, last["id"], wrong_answer(last))
    clock.advance(days=1)

    assert current_round(learner)["remaining"][0]["id"] == last["id"]


def test_answering_the_last_question_finishes_the_round(learner: TestClient) -> None:
    result = finish(learner, current_round(learner))

    assert result["round"]["state"] == "finished"
    assert result["round"]["finished_at"] == "2026-09-26T04:00:00Z"
    review = daily_review(learner)
    assert review["current"] is None
    assert [r["state"] for r in review["rounds"]] == ["finished"]
    assert code(answer(learner, result["round"], "w01-l01-q01", "a")) == (
        409,
        "review_round_finished",
    )


# --- A Pending Review Round locks the Unlocked Lesson --------------------------------------------


def test_an_optional_round_leaves_the_unlocked_lesson_unlocked(
    learner: TestClient, clock: FakeClock
) -> None:
    learner.get("/me")
    clock.advance(hours=1, minutes=59, seconds=59)

    assert lesson_states(learner) == {"w01-l01": "completed", "w01-l02": "unlocked"}
    assert learner.post(SECOND_QUIZ).status_code == 200


def test_two_hours_after_opening_the_round_is_pending_and_no_new_lesson_quiz_starts(
    learner: TestClient, clock: FakeClock
) -> None:
    round_ = current_round(learner)
    clock.advance(hours=2)

    refused = learner.post(SECOND_QUIZ)

    assert code(refused) == (409, "review_round_pending")
    assert refused.json()["detail"]["round_id"] == round_["id"]
    assert daily_review(learner)["rounds"][0]["state"] == "pending"


def test_the_week_map_says_the_unlocked_lesson_waits_for_the_pending_round(
    learner: TestClient, clock: FakeClock
) -> None:
    learner.get("/me")
    clock.advance(hours=3)

    week_map = learner.get("/stacks/mini-stack").json()

    [lessons] = [w["lessons"] for w in week_map["weeks"]]
    assert [
        (lesson["id"], lesson["state"], lesson["waiting_for_review"]) for lesson in lessons
    ] == [
        ("w01-l01", "completed", False),
        ("w01-l02", "locked", True),
    ]
    assert week_map["daily_review"]["rounds"][0]["state"] == "pending"
    lesson_page = learner.get("/stacks/mini-stack/lessons/w01-l02").json()
    assert (lesson_page["state"], lesson_page["waiting_for_review"]) == ("locked", True)


def test_a_lesson_quiz_in_progress_when_the_round_becomes_pending_can_be_finished(
    learner: TestClient, clock: FakeClock
) -> None:
    quiz = start(learner, SECOND_QUIZ)
    clock.advance(hours=2, minutes=30)

    result = submit(learner, quiz, answer_all(quiz), SECOND_QUIZ)

    assert result.status_code == 200, result.text
    assert result.json()["lesson_completed"] is True


def test_retakes_under_way_when_the_round_becomes_pending_can_be_finished(
    learner: TestClient, clock: FakeClock
) -> None:
    quiz = start(learner, SECOND_QUIZ)
    [retake] = submit(learner, quiz, answer_all(quiz, wrong=1), SECOND_QUIZ).json()["retakes"]
    clock.advance(hours=2)

    answered = learner.post(
        f"/stacks/mini-stack/lessons/w01-l02/retakes/{retake['id']}/answers", json={"answer": "a"}
    )

    assert answered.status_code == 200, answered.text
    assert answered.json()["lesson_completed"] is True


def test_finishing_the_pending_round_unlocks_the_lesson_again(
    learner: TestClient, clock: FakeClock
) -> None:
    round_ = current_round(learner)
    clock.advance(hours=4)

    result = finish(learner, round_)

    assert result["round"]["state"] == "finished"
    assert lesson_states(learner) == {"w01-l01": "completed", "w01-l02": "unlocked"}
    assert learner.post(SECOND_QUIZ).status_code == 200


def test_a_round_left_unfinished_yesterday_blocks_nothing_today(
    learner: TestClient, clock: FakeClock
) -> None:
    clock.set(datetime(2026, 9, 26, 17, 0, tzinfo=UTC))  # 23:00 in Dhaka
    yesterday = current_round(learner)
    clock.set(datetime(2026, 9, 26, 19, 30, tzinfo=UTC))  # 01:30 the next day in Dhaka

    assert learner.post(SECOND_QUIZ).status_code == 200
    question = yesterday["remaining"][0]["id"]
    assert code(answer(learner, yesterday, question, "a")) == (409, "review_round_dropped")
