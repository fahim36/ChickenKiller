"""Delayed outcomes count fresh recorded variants, never clicks or repeated answers."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from app.models import Question
from tests.conftest import (
    ContentFactory,
    FakeClock,
    FakeGrader,
    complete_lessons,
    mc_question,
    onboard,
)
from tests.test_lesson_quiz import start, submit
from tests.test_onboarding import activate, other_stack
from tests.test_retakes import answer_retake, miss

SUMMARY = "/admin/practice-outcomes"
TARGET = {"stack_id": "mini-stack", "concept_id": "concept-a"}
START = datetime(2026, 10, 1, 23, 59, tzinfo=UTC)


@pytest.fixture
def learner(session: Session, api: TestClient, make_content: ContentFactory) -> TestClient:
    def variants(_syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        bank["questions"].extend(
            [mc_question("w01-l01-q09", "concept-a"), mc_question("w01-l01-q10", "concept-a")]
        )

    import_folder(session, make_content(variants))
    onboard(api)
    complete_lessons(session, "w01-l01")
    return api


def answer(
    api: TestClient, qid: str, *, target: str | None = None, response: str | None = "a"
) -> None:
    result = api.post(
        "/review/answers",
        json={
            "stack_id": "mini-stack",
            "question_id": qid,
            "answer": response,
            "target_concept_id": target,
        },
    )
    assert result.status_code == 200, result.text


@pytest.mark.parametrize("days,expected", [(6, 0), (7, 1), (14, 1), (15, 0)])
def test_utc_delay_boundaries(
    learner: TestClient, admin: TestClient, clock: FakeClock, days: int, expected: int
) -> None:
    clock.set(START)
    answer(learner, "w01-l01-q01", target="concept-a")
    clock.set((START + timedelta(days=days)).replace(hour=0, minute=0))
    answer(learner, "w01-l01-q02")
    result = admin.get(SUMMARY)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["qualifying_answers"] == expected
    assert body["accuracy"] == (1.0 if expected else None)
    assert body["learners"] == expected
    assert body["concepts"] == expected


def test_click_is_not_practice_and_uptake_is_deduplicated_per_utc_day(
    learner: TestClient, admin: TestClient, clock: FakeClock
) -> None:
    clock.set(START)
    for _ in range(2):
        assert learner.post("/review/uptake", json=TARGET).status_code == 200
    body = admin.get(SUMMARY).json()
    assert body["uptake_days"] == 1
    assert body["completed_practice_answers"] == 0
    clock.set(START + timedelta(days=7))
    answer(learner, "w01-l01-q02")
    assert admin.get(SUMMARY).json()["qualifying_answers"] == 0
    assert learner.get(SUMMARY).status_code == 403


def test_latest_practice_overrides_older_eligible_practice_and_wrong_concept_is_refused(
    learner: TestClient, admin: TestClient, clock: FakeClock
) -> None:
    clock.set(START)
    answer(learner, "w01-l01-q01", target="concept-a")
    clock.set(START + timedelta(days=6))
    answer(learner, "w01-l01-q02", target="concept-a")
    clock.set(START + timedelta(days=7))
    answer(learner, "w01-l01-q09")
    assert admin.get(SUMMARY).json()["qualifying_answers"] == 0
    result = learner.post(
        "/review/answers",
        json={
            "stack_id": "mini-stack",
            "question_id": "w01-l01-q04",
            "answer": "a",
            "target_concept_id": "concept-a",
        },
    )
    assert result.status_code == 422


def test_repeats_retirement_and_unanswered_are_excluded(
    learner: TestClient, admin: TestClient, clock: FakeClock, session: Session
) -> None:
    clock.set(START)
    answer(learner, "w01-l01-q01", target="concept-a")
    answer(learner, "w01-l01-q02", response=None)
    clock.set(START + timedelta(days=7))
    answer(learner, "w01-l01-q01")
    answer(learner, "w01-l01-q02")
    answer(learner, "w01-l01-q09", response="b")
    body = admin.get(SUMMARY).json()
    assert body["qualifying_answers"] == 1
    assert body["correct_answers"] == 0
    assert body["accuracy"] == 0.0
    clock.set(START + timedelta(days=8))
    answer(learner, "w01-l01-q09")
    assert admin.get(SUMMARY).json()["qualifying_answers"] == 1
    q = session.scalars(select(Question).where(Question.id == "w01-l01-q09")).one()
    q.retired_reason = "Obsolete"
    session.commit()
    assert admin.get(SUMMARY).json()["qualifying_answers"] == 0


def test_empty_queue_unanswered_and_failed_grading_do_not_complete_practice(
    learner: TestClient, admin: TestClient, clock: FakeClock, grader: FakeGrader
) -> None:
    clock.set(START)
    answer(learner, "w01-l01-q01", target="concept-a", response=None)
    grader.failing = True
    failed = learner.post(
        "/review/answers",
        json={
            "stack_id": "mini-stack",
            "question_id": "w01-l01-q07",
            "answer": "right",
            "target_concept_id": "concept-d",
        },
    )
    assert failed.status_code == 503
    assert learner.post("/review/uptake", json={**TARGET, "concept_id": "missing"}).json() == {
        "recorded": False
    }
    body = admin.get(SUMMARY).json()
    assert body["completed_practice_answers"] == 0
    assert body["uptake_days"] == 0
    assert body["accuracy"] is None


def test_wrong_concept_answers_cannot_use_another_concepts_practice(
    learner: TestClient, admin: TestClient, clock: FakeClock
) -> None:
    clock.set(START)
    answer(learner, "w01-l01-q01", target="concept-a")
    clock.set(START + timedelta(days=7))
    answer(learner, "w01-l01-q03")
    assert admin.get(SUMMARY).json()["qualifying_answers"] == 0
    # Completing new practice at this timestamp cannot attribute its own answer to itself.
    answer(learner, "w01-l01-q04", target="concept-b")
    assert admin.get(SUMMARY).json()["qualifying_answers"] == 0


def test_retakes_completed_and_content_waivers_are_separate_supporting_counts(
    api: TestClient,
    admin: TestClient,
    clock: FakeClock,
    session: Session,
    make_content: ContentFactory,
) -> None:
    clock.set(START)
    import_folder(session, make_content())
    onboard(api)
    quiz = start(api)
    missed = next(q["id"] for q in quiz["questions"] if q["type"] == "multiple_choice")
    result = submit(api, quiz, miss(quiz, [missed])).json()
    [retake] = result["retakes"]
    assert answer_retake(api, retake, "a").status_code == 200
    body = admin.get(SUMMARY).json()
    assert body["retakes_total"] == body["retakes_completed"] == 1
    assert body["retakes_waived"] == 0
    assert body["qualifying_answers"] == 0

    onboard(admin)
    quiz = start(admin)
    missed = next(q["id"] for q in quiz["questions"] if q["type"] == "multiple_choice")
    result = submit(admin, quiz, miss(quiz, [missed])).json()
    question = session.scalars(select(Question).where(Question.id == missed)).one()
    question.retired_reason = "Removed"
    session.commit()
    resolved = admin.get(f"/stacks/mini-stack/lessons/w01-l01/quiz/{result['attempt_id']}/retakes")
    assert resolved.status_code == 200, resolved.text
    body = admin.get(SUMMARY).json()
    assert body["retakes_total"] == 2
    assert body["retakes_completed"] == body["retakes_waived"] == 1


def test_attribution_is_separate_per_learner_and_stack(
    learner: TestClient,
    admin: TestClient,
    session: Session,
    clock: FakeClock,
    make_content: ContentFactory,
) -> None:
    clock.set(START)
    answer(learner, "w01-l01-q01", target="concept-a")
    onboard(admin)
    complete_lessons(session, "w01-l01", email="admin@example.com")
    clock.set(START + timedelta(days=7))
    answer(admin, "w01-l01-q02")
    assert admin.get(SUMMARY).json()["qualifying_answers"] == 0
    import_folder(session, make_content(other_stack))
    activate(learner, "other-stack").raise_for_status()
    complete_lessons(session, "w01-l01", stack_id="other-stack")
    learner.post(
        "/review/answers",
        json={"stack_id": "other-stack", "question_id": "w01-l01-q02", "answer": "a"},
    ).raise_for_status()
    assert admin.get(SUMMARY).json()["qualifying_answers"] == 0
    activate(learner, "mini-stack").raise_for_status()
    answer(learner, "w01-l01-q02")
    body = admin.get(SUMMARY).json()
    assert body["qualifying_answers"] == body["learners"] == body["concepts"] == 1
