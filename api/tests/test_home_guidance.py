"""Home recommendations use private evidence and the existing due Review queue."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from app.models import Question
from tests.conftest import (
    ClientFactory,
    ContentFactory,
    FakeClock,
    complete_lessons,
    make_bank,
    onboard,
)
from tests.test_lesson_quiz import start, submit
from tests.test_onboarding import other_stack
from tests.test_retakes import miss, pass_missing_one
from tests.test_review import answer_right, answer_wrong

URL = "/home/guidance"
TARGET = "/review?stack_id=mini-stack&concept_id=concept-a"


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> TestClient:
    clock.set(datetime(2026, 10, 11, 10, tzinfo=UTC))
    import_folder(session, make_content(extra_banks={"w01-l02": make_bank("w01-l02", "second")}))
    onboard(api)
    return api


def guidance(client: TestClient) -> dict[str, Any]:
    response = client.get(URL)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_new_learner_gets_unlocked_lesson_with_optional_reason(learner: TestClient) -> None:
    result = guidance(learner)
    assert result["action"]["kind"] == "lesson"
    assert result["action"]["lesson_id"] == "w01-l01"
    assert result["action"]["reason"]
    assert result["weak_concepts"] == []


def test_weak_concept_review_outranks_unlocked_lesson_and_uses_existing_answers(
    session: Session, learner: TestClient, clock: FakeClock
) -> None:
    complete_lessons(session, "w01-l01")
    answer_wrong(learner, "w01-l01-q01")
    answer_wrong(learner, "w01-l01-q02")
    result = guidance(learner)
    assert result["action"]["kind"] == "concept_review"
    assert result["action"]["concept_id"] == "concept-a"
    assert result["weak_concepts"][0]["recent_missed_questions"] == 2
    targeted = learner.get(TARGET)
    assert targeted.status_code == 200
    assert {q["id"] for q in targeted.json()["questions"]} == {"w01-l01-q01", "w01-l01-q02"}
    clock.advance(seconds=1)
    answer_right(learner, "w01-l01-q01")
    answer_right(learner, "w01-l01-q02")
    assert learner.get(TARGET).json()["questions"] == []
    assert guidance(learner)["action"]["kind"] == "lesson"


def test_retakes_win_and_retired_original_is_reconciled_before_recommending(
    session: Session, learner: TestClient
) -> None:
    missed, state = pass_missing_one(learner)
    result = guidance(learner)
    assert result["action"]["kind"] == "retake"
    assert result["action"]["attempt_id"] == state["attempt_id"]
    session.scalars(
        select(Question).where(Question.id == missed)
    ).one().retired_reason = "Invalid premise."
    session.commit()
    assert guidance(learner)["action"]["kind"] != "retake"


def test_completed_stacks_offer_due_review_then_materials_and_milestones(
    session: Session, learner: TestClient
) -> None:
    complete_lessons(session, "w01-l01", "w01-l02")
    assert guidance(learner)["action"]["kind"] == "review"
    for lesson in ("w01-l01", "w01-l02"):
        for n in range(1, 9):
            answer_right(learner, f"{lesson}-q{n:02}")
    result = guidance(learner)
    assert result["action"]["kind"] == "complete"
    assert result["stacks"][0]["stack_id"] == "mini-stack"
    assert result["action"]["reason"]


def test_targeted_review_does_not_unlock_locked_lesson_or_non_due_questions(
    learner: TestClient,
) -> None:
    assert learner.get(TARGET).json()["questions"] == []
    assert (
        learner.post(
            "/review/answers",
            json={"stack_id": "mini-stack", "question_id": "w01-l01-q01", "answer": "a"},
        ).status_code
        == 409
    )
    assert learner.get("/review?concept_id=concept-a").status_code == 422
    assert learner.get("/review?stack_id=mini-stack&concept_id=unknown").status_code == 404


def test_no_activity_ties_are_stable_and_recent_practice_selects_its_stack(
    session: Session, learner: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    import_folder(session, make_content(other_stack))
    onboard(learner, "other-stack", "mini-stack")
    assert guidance(learner)["action"]["stack_id"] == "mini-stack"
    complete_lessons(session, "w01-l01", stack_id="other-stack")
    response = learner.post(
        "/review/answers",
        json={"stack_id": "other-stack", "question_id": "w01-l01-q01", "answer": "a"},
    )
    assert response.status_code == 200
    assert guidance(learner)["action"]["stack_id"] == "other-stack"
    onboard(learner, "mini-stack")
    assert guidance(learner)["action"]["stack_id"] == "mini-stack"
    assert learner.get("/review?stack_id=other-stack&concept_id=concept-a").status_code == 409


def test_another_learner_cannot_see_private_weak_evidence(
    session: Session, learner: TestClient, signed_in: ClientFactory
) -> None:
    complete_lessons(session, "w01-l01")
    answer_wrong(learner, "w01-l01-q01")
    answer_wrong(learner, "w01-l01-q02")
    other = signed_in("admin@example.com")
    onboard(other)
    assert guidance(other)["weak_concepts"] == []


def test_targeted_review_filters_before_the_ten_question_limit(
    session: Session, learner: TestClient
) -> None:
    complete_lessons(session, "w01-l01", "w01-l02")
    response = learner.get("/review?stack_id=mini-stack&concept_id=second-c")
    assert response.status_code == 200
    assert {q["id"] for q in response.json()["questions"]} == {"w01-l02-q05", "w01-l02-q06"}


def test_oldest_pending_retakes_win_across_active_stacks(
    session: Session, learner: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    import_folder(session, make_content(other_stack))
    onboard(learner, "other-stack", "mini-stack")
    _, first = pass_missing_one(learner)
    clock.advance(minutes=1)
    url = "/stacks/other-stack/lessons/w01-l01/quiz"
    attempt = start(learner, url)
    missed = attempt["questions"][0]["id"]
    second = submit(learner, attempt, miss(attempt, [missed]), url)
    assert second.status_code == 200
    result = guidance(learner)["action"]
    assert result["kind"] == "retake"
    assert result["stack_id"] == "mini-stack"
    assert result["attempt_id"] == first["attempt_id"]


def test_home_caps_ranked_weak_concepts_at_three_and_breaks_equal_misses_by_id(
    session: Session, learner: TestClient, clock: FakeClock
) -> None:
    complete_lessons(session, "w01-l01")
    for n in range(1, 9):
        answer_wrong(learner, f"w01-l01-q{n:02}")
    result = guidance(learner)
    assert [c["id"] for c in result["weak_concepts"]] == ["concept-a", "concept-b", "concept-c"]
    assert result["action"]["concept_id"] == "concept-a"
    clock.advance(seconds=1)
    answer_wrong(learner, "w01-l01-q08")
    assert guidance(learner)["weak_concepts"][0]["id"] == "concept-d"


def test_home_requires_onboarding(api: TestClient) -> None:
    assert api.get(URL).status_code == 409
