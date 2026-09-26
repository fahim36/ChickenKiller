"""The Daily Review over the API (#9): Round 1 opening on the first use of the Day (UTC,
ADR-0005); its Questions; answering them one at a time; and a Pending Review Round
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
from tests.test_onboarding import other_stack

REVIEW = "/stacks/mini-stack/review"
SECOND_QUIZ = "/stacks/mini-stack/lessons/w01-l02/quiz"
FIRST_BANK = {f"w01-l01-q{n:02}" for n in range(1, 9)}
FIRST_WRITTEN = {"w01-l01-q07", "w01-l01-q08"}

# 10:00 UTC on 26 September.
MORNING = datetime(2026, 9, 26, 10, 0, tzinfo=UTC)


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> TestClient:
    """A Learner on the mini Stack, whose first Lesson (w01-l01) is a Completed Lesson, and
    who hasn't used the app yet today. It is 10:00 UTC."""
    clock.set(MORNING)
    import_folder(session, make_content(extra_banks={"w01-l02": make_bank("w01-l02", "second")}))
    onboard(api)
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
        "opened_at": "2026-09-26T10:00:00Z",
        "pending_at": "2026-09-26T12:00:00Z",
        "finished_at": None,
        "answered": 0,
        "total": 8,
    }
    current = review["current"]
    assert current["id"] == summary["id"]
    assert {q["id"] for q in current["remaining"]} == FIRST_BANK
    assert current["results"] == []
    assert current["max_answer_chars"] == 4000


def test_each_active_stack_opens_its_own_round_1(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    clock.set(MORNING)
    import_folder(session, make_content())
    import_folder(session, make_content(other_stack))
    onboard(api, "mini-stack", "other-stack")
    complete_lessons(session, "w01-l01")
    complete_lessons(session, "w01-l01", stack_id="other-stack")

    api.get("/me")

    for stack_id in ["mini-stack", "other-stack"]:
        review = api.get(f"/stacks/{stack_id}/review").json()
        assert [(r["number"], r["opened_at"]) for r in review["rounds"]] == [
            (1, "2026-09-26T10:00:00Z")
        ]


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
    clock.advance(hours=13, minutes=59)  # 23:59

    rounds = daily_review(learner)["rounds"]

    assert [r["id"] for r in rounds] == [first[0]["id"]]


def test_the_next_day_starts_at_midnight_utc_with_a_new_round_1(
    learner: TestClient, clock: FakeClock
) -> None:
    clock.set(datetime(2026, 9, 26, 23, 59, 59, tzinfo=UTC))  # 23:59:59
    yesterday = daily_review(learner)
    clock.advance(seconds=1)  # midnight UTC

    today = daily_review(learner)

    assert (yesterday["day"], today["day"]) == ("2026-09-26", "2026-09-27")
    [round_1] = today["rounds"]
    assert round_1["number"] == 1
    assert round_1["id"] != yesterday["rounds"][0]["id"]
    assert round_1["opened_at"] == "2026-09-27T00:00:00Z"


def test_a_learner_with_no_completed_lesson_gets_no_daily_review(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    clock.set(MORNING)
    import_folder(session, make_content())
    onboard(api)

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
    onboard(api)
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
    onboard(api)
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
    finish(learner, current_round(learner))  # nothing carries over (#10)
    clock.advance(days=1)

    assert current_round(learner)["remaining"][0]["id"] == last["id"]


def test_answering_the_last_question_finishes_the_round(learner: TestClient) -> None:
    result = finish(learner, current_round(learner))

    assert result["round"]["state"] == "finished"
    assert result["round"]["finished_at"] == "2026-09-26T10:00:00Z"
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
    clock.set(datetime(2026, 9, 26, 23, 0, tzinfo=UTC))  # 23:00
    yesterday = current_round(learner)
    clock.set(datetime(2026, 9, 27, 1, 30, tzinfo=UTC))  # 01:30 the next day

    assert learner.post(SECOND_QUIZ).status_code == 200
    question = yesterday["remaining"][0]["id"]
    assert code(answer(learner, yesterday, question, "a")) == (409, "review_round_dropped")


# --- Rounds 2 and 3 (#10) ----------------------------------------------------------------------


def rounds(client: TestClient) -> list[tuple[int, str]]:
    return [(r["number"], r["state"]) for r in daily_review(client)["rounds"]]


def test_round_2_opens_four_hours_after_round_1_is_finished(
    learner: TestClient, clock: FakeClock
) -> None:
    finish(learner, current_round(learner))  # at 10:00
    clock.advance(hours=3, minutes=59, seconds=59)

    before = daily_review(learner)
    clock.advance(seconds=1)
    after = daily_review(learner)

    assert (before["current"], before["next_round_at"]) == (None, "2026-09-26T14:00:00Z")
    assert [r["number"] for r in before["rounds"]] == [1]
    round_2 = after["rounds"][1]
    assert (round_2["number"], round_2["state"]) == (2, "optional")
    assert (round_2["opened_at"], round_2["pending_at"]) == (
        "2026-09-26T14:00:00Z",
        "2026-09-26T16:00:00Z",
    )
    assert after["current"]["id"] == round_2["id"]
    assert after["next_round_at"] is None


def test_round_2_is_pending_two_hours_after_it_opens_and_blocks_the_next_lesson_quiz(
    learner: TestClient, clock: FakeClock
) -> None:
    finish(learner, current_round(learner))
    clock.advance(hours=4)
    round_2 = current_round(learner)
    clock.advance(hours=1, minutes=59)
    assert learner.post(SECOND_QUIZ).status_code == 200  # still optional; this quiz may finish
    clock.advance(minutes=1)

    refused = learner.post(SECOND_QUIZ)

    assert rounds(learner) == [(1, "finished"), (2, "pending")]
    assert code(refused) == (409, "review_round_pending")
    assert refused.json()["detail"]["round_id"] == round_2["id"]


def test_a_round_opens_on_time_even_while_the_learner_is_away(
    learner: TestClient, clock: FakeClock
) -> None:
    """Nobody asks at 14:00, so the round is stored on the next request, but it opened at
    14:00: back at 16:30, it is already pending."""
    finish(learner, current_round(learner))
    clock.advance(hours=6, minutes=30)

    review = daily_review(learner)

    round_2 = review["rounds"][1]
    assert (round_2["opened_at"], round_2["state"]) == ("2026-09-26T14:00:00Z", "pending")
    assert code(learner.post(SECOND_QUIZ)) == (409, "review_round_pending")


def test_no_round_opens_while_the_previous_one_is_unfinished(
    learner: TestClient, clock: FakeClock
) -> None:
    round_1 = current_round(learner)
    answer(learner, round_1, round_1["remaining"][0]["id"], "a")
    clock.advance(hours=10)

    review = daily_review(learner)

    assert rounds(learner) == [(1, "pending")]
    assert review["next_round_at"] is None


def test_a_full_day_has_three_rounds_and_no_fourth(learner: TestClient, clock: FakeClock) -> None:
    opened = []
    for _ in range(3):
        round_ = current_round(learner)
        opened.append(round_["opened_at"])
        finish(learner, round_)
        clock.advance(hours=4)

    review = daily_review(learner)

    assert opened == ["2026-09-26T10:00:00Z", "2026-09-26T14:00:00Z", "2026-09-26T18:00:00Z"]
    assert rounds(learner) == [(1, "finished"), (2, "finished"), (3, "finished")]
    assert (review["current"], review["next_round_at"]) == (None, None)
    assert learner.post(SECOND_QUIZ).status_code == 200


def test_using_the_app_all_day_opens_only_three_rounds(
    learner: TestClient, clock: FakeClock
) -> None:
    clock.set(datetime(2026, 9, 26, 0, 0, tzinfo=UTC))  # midnight
    for _ in range(24 * 4 - 1):  # every 15 minutes until 23:45, finishing each round at once
        current = daily_review(learner)["current"]
        if current is not None:
            finish(learner, current)
        clock.advance(minutes=15)

    assert rounds(learner) == [(1, "finished"), (2, "finished"), (3, "finished")]


def test_a_round_that_would_open_after_midnight_does_not_open(
    learner: TestClient, clock: FakeClock
) -> None:
    clock.set(datetime(2026, 9, 26, 20, 30, tzinfo=UTC))  # 20:30
    finish(learner, current_round(learner))

    assert daily_review(learner)["next_round_at"] is None
    clock.advance(hours=3, minutes=29)  # 23:59
    assert rounds(learner) == [(1, "finished")]


def test_every_round_asks_the_completed_lessons_questions(
    learner: TestClient, clock: FakeClock
) -> None:
    """The mini Stack has only eight Questions of Completed Lessons, so once Round 1 has asked
    them all, Round 2 asks them again rather than nothing."""
    finish(learner, current_round(learner))
    clock.advance(hours=4)

    assert {q["id"] for q in current_round(learner)["remaining"]} == FIRST_BANK


# --- Carry-over (#10) ----------------------------------------------------------------------------


def leave_round_2_half_done(learner: TestClient, clock: FakeClock) -> tuple[list[str], str]:
    """Finish Round 1 at 10:00, then answer three of Round 2's Questions at 14:00 (the
    first one wrong) and leave the rest. The unanswered Questions in order, and the missed one."""
    finish(learner, current_round(learner))
    clock.advance(hours=4)
    round_2 = current_round(learner)
    asked = round_2["remaining"]
    answer(learner, round_2, asked[0]["id"], wrong_answer(asked[0]))
    for question in asked[1:3]:
        answer(learner, round_2, question["id"], right_answer(question))
    return [q["id"] for q in asked[3:]], asked[0]["id"]


def test_an_unfinished_round_is_dropped_and_its_unanswered_questions_lead_the_next_day(
    learner: TestClient, clock: FakeClock
) -> None:
    unanswered, missed = leave_round_2_half_done(learner, clock)
    yesterday = current_round(learner)
    clock.set(datetime(2026, 9, 27, 0, 0, tzinfo=UTC))  # midnight

    today = daily_review(learner)

    assert today["day"] == "2026-09-27"
    [round_1] = today["rounds"]
    assert round_1["number"] == 1
    remaining = [q["id"] for q in today["current"]["remaining"]]
    assert remaining[: len(unanswered)] == unanswered
    assert remaining[len(unanswered)] == missed  # Missed Questions come after the carry-over
    question = yesterday["remaining"][0]["id"]
    assert code(answer(learner, yesterday, question, "a")) == (409, "review_round_dropped")


def test_a_round_left_optional_at_midnight_is_dropped_too(
    learner: TestClient, clock: FakeClock
) -> None:
    clock.set(datetime(2026, 9, 26, 23, 30, tzinfo=UTC))  # 23:30
    first = current_round(learner)
    asked = [q["id"] for q in first["remaining"]]
    answer_by_id(learner, first, asked[0], right=True)
    clock.advance(hours=1)  # 00:30

    remaining = [q["id"] for q in current_round(learner)["remaining"]]

    assert remaining[:7] == asked[1:]


def test_carried_over_questions_wait_for_the_learner_s_next_day_with_rounds(
    learner: TestClient, clock: FakeClock
) -> None:
    unanswered, _ = leave_round_2_half_done(learner, clock)
    clock.advance(days=3)

    remaining = [q["id"] for q in current_round(learner)["remaining"]]

    assert remaining[: len(unanswered)] == unanswered


# --- Leaving the rotation (#10) ------------------------------------------------------------------


def answer_by_id(
    client: TestClient, round_: dict[str, Any], question_id: str, *, right: bool
) -> None:
    question = next(q for q in round_["remaining"] if q["id"] == question_id)
    given = right_answer(question) if right else wrong_answer(question)
    response = answer(client, round_, question_id, given)
    assert response.status_code == 200, response.text


def test_a_missed_question_leaves_the_rotation_after_correct_answers_on_three_days(
    learner: TestClient, clock: FakeClock
) -> None:
    """q01 is missed on day 1, then answered correctly on days 2, 3 and 4; q02 is missed every
    day. Both lead the round while in the rotation, first missed first; on day 5 q01 has left
    it, so q02 leads alone. Each day's round is finished, so nothing carries over."""
    round_ = current_round(learner)
    answer_by_id(learner, round_, "w01-l01-q01", right=False)
    answer_by_id(learner, round_, "w01-l01-q02", right=False)
    finish(learner, current_round(learner))
    leads = []
    for _ in range(3):
        clock.advance(days=1)
        round_ = current_round(learner)
        leads.append([q["id"] for q in round_["remaining"][:2]])
        answer_by_id(learner, round_, "w01-l01-q01", right=True)
        answer_by_id(learner, round_, "w01-l01-q02", right=False)
        finish(learner, current_round(learner))
    clock.advance(days=1)

    assert leads == [["w01-l01-q01", "w01-l01-q02"]] * 3
    assert current_round(learner)["remaining"][0]["id"] == "w01-l01-q02"


def test_correct_answers_on_one_day_count_once_towards_leaving_the_rotation(
    learner: TestClient, clock: FakeClock
) -> None:
    """Missed in Round 1, then right in Rounds 2 and 3 the same day and in Round 1 the next day:
    three correct answers, but on two days, so it still leads on the third day."""
    round_ = current_round(learner)
    answer_by_id(learner, round_, "w01-l01-q01", right=False)
    finish(learner, current_round(learner))
    for _ in range(2):  # Rounds 2 and 3
        clock.advance(hours=4)
        round_ = current_round(learner)
        answer_by_id(learner, round_, "w01-l01-q01", right=True)
        finish(learner, current_round(learner))
    clock.advance(days=1)
    round_ = current_round(learner)
    assert round_["remaining"][0]["id"] == "w01-l01-q01"
    answer_by_id(learner, round_, "w01-l01-q01", right=True)
    finish(learner, current_round(learner))
    clock.advance(days=1)

    assert current_round(learner)["remaining"][0]["id"] == "w01-l01-q01"
