"""Review over the API (#9): an optional queue of Questions across all Active Stacks, drawn in
sets of up to ten and answered one at a time. It has no rounds or timers and never blocks
anything. The clock is the test's (`clock`, conftest.py), so Days (UTC, ADR-0005) turn only
when a test moves it. The rules themselves are tested in test_review_rules.py.

The mini Stack's Lessons each have a bank of eight Questions: six multiple choice (choice "a"
is right) and two written (the fake grader passes an answer saying "right")."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy.orm import Session

from app import quizzes
from app.content.importer import import_folder
from tests.conftest import (
    ContentFactory,
    FakeClock,
    FakeGrader,
    complete_lessons,
    make_bank,
    mc_question,
    onboard,
)
from tests.test_lesson_quiz import (
    RIGHT,
    WRONG,
    answer_all,
    code,
    keys,
    learner_id,
    lesson_states,
    start,
    submit,
)
from tests.test_onboarding import other_stack

FIRST_BANK = [f"w01-l01-q{n:02}" for n in range(1, 9)]
FIRST_QUIZ = "/stacks/mini-stack/lessons/w01-l01/quiz"
SECOND_QUIZ = "/stacks/mini-stack/lessons/w01-l02/quiz"

# 10:00 UTC on 26 September.
MORNING = datetime(2026, 9, 26, 10, 0, tzinfo=UTC)


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> TestClient:
    """A Learner on the mini Stack whose first Lesson (w01-l01) is a Completed Lesson, with no
    answers given yet. It is 10:00 UTC."""
    clock.set(MORNING)
    import_folder(session, make_content(extra_banks={"w01-l02": make_bank("w01-l02", "second")}))
    onboard(api)
    complete_lessons(session, "w01-l01")
    return api


def review_set(client: TestClient) -> list[dict[str, Any]]:
    response = client.get("/review")
    assert response.status_code == 200, response.text
    questions: list[dict[str, Any]] = response.json()["questions"]
    return questions


def asked(client: TestClient) -> list[str]:
    return [q["id"] for q in review_set(client)]


def answer(
    client: TestClient, question_id: str, response: str | None, stack_id: str = "mini-stack"
) -> Response:
    return client.post(
        "/review/answers",
        json={"stack_id": stack_id, "question_id": question_id, "answer": response},
    )


def is_written(question_id: str) -> bool:
    return question_id.endswith(("q07", "q08"))


def answer_right(client: TestClient, question_id: str, stack_id: str = "mini-stack") -> None:
    given = RIGHT if is_written(question_id) else "a"
    response = answer(client, question_id, given, stack_id)
    assert response.status_code == 200, response.text
    assert response.json()["correct"] is True


def answer_wrong(client: TestClient, question_id: str, stack_id: str = "mini-stack") -> None:
    given = WRONG if is_written(question_id) else "b"
    response = answer(client, question_id, given, stack_id)
    assert response.status_code == 200, response.text
    assert response.json()["correct"] is False


# --- Drawing a set -----------------------------------------------------------------------------


def test_a_learner_with_nothing_to_review_gets_an_empty_set(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content())
    onboard(api)

    body = api.get("/review").json()

    assert body == {"size": 10, "max_answer_chars": 4000, "questions": []}


def test_review_needs_onboarding_first(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content())

    assert code(api.get("/review")) == (409, "onboarding_needed")


def test_the_completed_lessons_questions_come_as_spaced_repeats_in_syllabus_order(
    learner: TestClient,
) -> None:
    questions = review_set(learner)

    assert [q["id"] for q in questions] == FIRST_BANK
    assert questions[0] == {
        "stack_id": "mini-stack",
        "stack_name": "Mini Stack",
        "id": "w01-l01-q01",
        "type": "multiple_choice",
        "prompt": "Question 1?",
        "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
    }


def test_a_set_s_questions_come_without_their_answers(learner: TestClient) -> None:
    response = learner.get("/review")

    assert keys(response.json()["questions"]).isdisjoint(
        {"answer", "explanation", "model_answer", "key_points", "summary"}
    )
    assert "Because." not in response.text


def test_a_set_holds_at_most_ten_questions(session: Session, learner: TestClient) -> None:
    complete_lessons(session, "w01-l02")

    assert asked(learner) == [*FIRST_BANK, "w01-l02-q01", "w01-l02-q02"]


def retire_q01(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    """w01-l01-q01 is retired and replaced by a new q09."""
    bank["questions"][0]["retired"] = {"reason": "Wrong.", "replaced_by": "w01-l01-q09"}
    bank["questions"].append(mc_question("w01-l01-q09", "concept-a"))


def test_a_retired_question_is_never_drawn_nor_answered(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    import_folder(
        session,
        make_content(retire_q01, extra_banks={"w01-l02": make_bank("w01-l02", "second")}),
    )

    questions = asked(learner)

    assert "w01-l01-q01" not in questions
    assert "w01-l01-q09" in questions
    assert code(answer(learner, "w01-l01-q01", "a")) == (409, "not_in_review")


def test_a_missed_question_retired_later_leaves_review(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    answer_wrong(learner, "w01-l01-q01")
    assert asked(learner)[0] == "w01-l01-q01"

    import_folder(
        session,
        make_content(retire_q01, extra_banks={"w01-l02": make_bank("w01-l02", "second")}),
    )

    assert "w01-l01-q01" not in asked(learner)


def test_locked_lessons_questions_are_never_drawn(learner: TestClient) -> None:
    assert not [q for q in asked(learner) if q.startswith("w01-l02")]


def test_drawing_a_set_changes_nothing(learner: TestClient) -> None:
    """Sets aren't stored: asking again draws the same set until something is answered."""
    assert asked(learner) == asked(learner)


def test_missed_questions_come_first_oldest_first_across_active_stacks(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    """The same Question IDs on two Stacks are two Questions: each is asked on its own Stack."""
    clock.set(MORNING)
    import_folder(session, make_content())
    import_folder(session, make_content(other_stack))
    onboard(api, "mini-stack", "other-stack")
    other_quiz = "/stacks/other-stack/lessons/w01-l01/quiz"
    first = start(api, other_quiz)
    submit(api, first, answer_all(first, wrong=1), other_quiz)
    clock.advance(minutes=5)
    second = start(api, FIRST_QUIZ)
    submit(api, second, answer_all(second, wrong=2), FIRST_QUIZ)

    questions = review_set(api)

    assert [(q["stack_id"], q["id"]) for q in questions] == [
        ("other-stack", first["questions"][0]["id"]),
        ("mini-stack", second["questions"][0]["id"]),
        ("mini-stack", second["questions"][1]["id"]),
    ]
    assert questions[0]["stack_name"] == "Other Stack"


def test_missed_questions_lead_the_completed_lessons_repeats(
    learner: TestClient, clock: FakeClock
) -> None:
    answer_wrong(learner, "w01-l01-q05")

    assert asked(learner)[0] == "w01-l01-q05"


def test_a_deactivated_stack_s_questions_leave_review(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    clock.set(MORNING)
    import_folder(session, make_content())
    import_folder(session, make_content(other_stack))
    onboard(api, "mini-stack", "other-stack")
    complete_lessons(session, "w01-l01", stack_id="other-stack")
    assert {q["stack_id"] for q in review_set(api)} == {"other-stack"}

    onboard(api, "mini-stack")

    assert review_set(api) == []
    assert code(answer(api, "w01-l01-q01", "a", "other-stack")) == (409, "not_active_stack")


# --- Answering ---------------------------------------------------------------------------------


def test_a_right_answer_is_marked_correct_and_recorded_as_a_review_answer(
    session: Session, learner: TestClient
) -> None:
    result = answer(learner, "w01-l01-q01", "a").json()

    assert result["correct"] is True
    assert result["question"]["id"] == "w01-l01-q01"
    [recorded] = quizzes.recorded_answers(session, learner_id(session), "mini-stack")
    assert (recorded.context, recorded.question_id, recorded.response, recorded.correct) == (
        "review",
        "w01-l01-q01",
        "a",
        True,
    )


def test_a_wrong_answer_shows_its_explanation_and_correct_answer(learner: TestClient) -> None:
    result = answer(learner, "w01-l01-q01", "b").json()

    assert result["correct"] is False
    assert result["question"] == {
        "id": "w01-l01-q01",
        "type": "multiple_choice",
        "prompt": "Question 1?",
        "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
        "response": "b",
        "selected": [],
        "feedback": None,
        "answer": "a",
        "answers": [],
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
        "sources": [
            {
                "url": "https://example.com/docs/page-1",
                "title": "Docs page 1",
                "publisher": "Example",
                "accessed": "2026-01-01",
                "claim": "What the Question relies on.",
            }
        ],
    }


def test_a_written_answer_is_graded_and_a_miss_shows_the_model_answer_and_feedback(
    learner: TestClient,
) -> None:
    missed = answer(learner, "w01-l01-q07", WRONG).json()
    passed = answer(learner, "w01-l01-q08", RIGHT).json()

    assert missed["correct"] is False
    assert missed["question"]["feedback"] == "Missing: one."
    assert missed["question"]["model_answer"] == {"summary": "S", "key_points": ["one", "two"]}
    assert missed["question"]["explanation"] == "Because."
    assert (passed["correct"], passed["question"]["feedback"]) == (True, "Covers every key point.")


def test_when_grading_fails_nothing_is_recorded_and_the_learner_answers_again(
    session: Session, learner: TestClient, grader: FakeGrader
) -> None:
    grader.failing = True
    failed = answer(learner, "w01-l01-q07", RIGHT)
    grader.failing = False
    assert quizzes.recorded_answers(session, learner_id(session), "mini-stack") == []

    retried = answer(learner, "w01-l01-q07", RIGHT)

    assert code(failed) == (503, "grading_failed")
    assert (retried.status_code, retried.json()["correct"]) == (200, True)


def test_answers_that_do_not_fit_the_question_are_rejected(learner: TestClient) -> None:
    assert code(answer(learner, "w01-l01-q01", "z")) == (422, "not_a_choice")
    assert code(answer(learner, "w01-l01-q07", "x" * 4001)) == (422, "answer_too_long")


def test_a_question_that_is_not_in_the_learner_s_review_is_refused(learner: TestClient) -> None:
    """A Locked Lesson's Question, an unknown one, and a repeat already answered today."""
    answer_right(learner, "w01-l01-q01")

    assert code(answer(learner, "w01-l02-q01", "a")) == (409, "not_in_review")
    assert code(answer(learner, "no-such-question", "a")) == (409, "not_in_review")
    assert code(answer(learner, "w01-l01-q01", "a")) == (409, "not_in_review")


def test_an_unknown_stack_is_not_found(learner: TestClient) -> None:
    assert answer(learner, "w01-l01-q01", "a", "no-such-stack").status_code == 404


def test_an_answered_repeat_leaves_the_set_and_comes_back_three_days_later(
    learner: TestClient, clock: FakeClock
) -> None:
    answer_right(learner, "w01-l01-q01")
    assert asked(learner) == FIRST_BANK[1:]

    clock.advance(days=2)
    assert "w01-l01-q01" not in asked(learner)
    clock.advance(days=1)
    assert asked(learner)[-1] == "w01-l01-q01"  # the least recently answered come first


def test_a_wrong_answer_makes_a_missed_question_that_leads_the_next_set(
    learner: TestClient,
) -> None:
    answer_wrong(learner, "w01-l01-q08")

    assert asked(learner)[0] == "w01-l01-q08"


# --- Leaving the queue: correct on three different Days ----------------------------------------


def test_a_missed_question_leaves_the_queue_after_correct_answers_on_three_days(
    learner: TestClient, clock: FakeClock
) -> None:
    """q01 is missed on day 1 and answered correctly on days 2, 3 and 4; q02 is missed on day 1
    and every day after. Both lead the set while in the queue, oldest first; after day 4 q01
    has left it (and, answered on day 4, isn't a repeat again until day 7)."""
    answer_wrong(learner, "w01-l01-q01")
    answer_wrong(learner, "w01-l01-q02")
    leads = []
    for _ in range(3):
        clock.advance(days=1)
        leads.append(asked(learner)[:2])
        answer_right(learner, "w01-l01-q01")
        answer_wrong(learner, "w01-l01-q02")
    clock.advance(days=1)

    assert leads == [["w01-l01-q01", "w01-l01-q02"]] * 3
    assert asked(learner)[0] == "w01-l01-q02"
    assert "w01-l01-q01" not in asked(learner)


def test_a_missed_question_answered_correctly_waits_for_the_next_day(
    learner: TestClient, clock: FakeClock
) -> None:
    """A second correct answer the same Day couldn't count towards a new Day."""
    answer_wrong(learner, "w01-l01-q01")
    clock.advance(days=1)
    answer_right(learner, "w01-l01-q01")

    assert "w01-l01-q01" not in asked(learner)
    assert code(answer(learner, "w01-l01-q01", "a")) == (409, "not_in_review")
    clock.set(datetime(2026, 9, 28, 0, 0, tzinfo=UTC))  # the next Day starts at midnight UTC
    assert asked(learner)[0] == "w01-l01-q01"


def test_correct_answers_in_a_lesson_quiz_count_towards_leaving_the_queue(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    """Missed on a failed Lesson Quiz, then right in the fresh quiz the next day: that Day
    counts, so two more Days in Review take it out of the queue."""
    clock.set(MORNING)
    import_folder(session, make_content())
    onboard(api)
    failed = start(api, FIRST_QUIZ)
    submit(api, failed, answer_all(failed, wrong=6), FIRST_QUIZ)
    missed = failed["questions"][4]["id"]  # written: every quiz asks both of the bank's two
    clock.advance(days=1)
    fresh = start(api, FIRST_QUIZ)
    submit(api, fresh, answer_all(fresh), FIRST_QUIZ)
    assert missed in {q["id"] for q in fresh["questions"]}
    for _ in range(2):
        clock.advance(days=1)
        answer_right(api, missed)
    clock.advance(days=1)

    assert missed not in asked(api)


# --- Review never blocks -----------------------------------------------------------------------


def test_review_left_undone_blocks_nothing(learner: TestClient, clock: FakeClock) -> None:
    answer_wrong(learner, "w01-l01-q01")
    clock.advance(days=3, hours=5)

    assert review_set(learner)  # still owed, and it doesn't matter
    assert lesson_states(learner) == {"w01-l01": "completed", "w01-l02": "unlocked"}
    assert learner.post(SECOND_QUIZ).status_code == 200


def test_the_week_map_has_no_daily_review_or_streak(learner: TestClient) -> None:
    week_map = learner.get("/stacks/mini-stack").json()
    lesson_page = learner.get("/stacks/mini-stack/lessons/w01-l02").json()

    assert keys(week_map).isdisjoint({"daily_review", "streak", "waiting_for_review"})
    assert "waiting_for_review" not in lesson_page
