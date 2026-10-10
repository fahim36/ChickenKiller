"""Private Concept guidance over the API; outcomes are made through existing Review."""

from datetime import UTC, datetime

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
    FakeGrader,
    complete_lessons,
    onboard,
)
from tests.test_daily_challenge import MC1, MC2, MORNING, WRITTEN, import_stack, today
from tests.test_daily_challenge import answer as challenge_answer
from tests.test_onboarding import other_stack
from tests.test_retakes import answer_retake, pass_missing_one
from tests.test_review import answer, answer_right, answer_wrong

URL = "/stacks/mini-stack/concept-evidence"


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> TestClient:
    clock.set(datetime(2026, 10, 3, 10, tzinfo=UTC))
    import_folder(session, make_content())
    onboard(api)
    complete_lessons(session, "w01-l01")
    return api


def concept(client: TestClient, concept_id: str = "concept-a") -> dict[str, object]:
    result = client.get(URL)
    assert result.status_code == 200, result.text
    return next(c for c in result.json()["concepts"] if c["id"] == concept_id)


def test_two_answered_sibling_misses_show_private_weak_evidence_and_a_lesson_link(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    clock.set(datetime(2026, 10, 3, 10, tzinfo=UTC))
    import_folder(session, make_content())
    onboard(api)
    complete_lessons(session, "w01-l01")
    answer_wrong(api, "w01-l01-q01")
    answer_wrong(api, "w01-l01-q02")
    response = api.get(URL)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["as_of"] == "2026-10-03"
    concept = result["concepts"][0]
    assert concept["id"] == "concept-a"
    assert concept["status"] == "weak"
    assert concept["recent_missed_questions"] == 2
    assert concept["lesson_id"] == "w01-l01"
    assert concept["active_questions"] == 2
    assert concept["recovery_days"] == 0


def test_unanswered_repeated_misses_and_retired_questions_do_not_inflate_evidence(
    session: Session, learner: TestClient
) -> None:
    answer_wrong(learner, "w01-l01-q01")
    answer_wrong(learner, "w01-l01-q01")
    assert answer(learner, "w01-l01-q02", None).status_code == 200
    assert concept(learner)["status"] == "insufficient"
    assert concept(learner)["recent_missed_questions"] == 1
    answer_wrong(learner, "w01-l01-q02")
    assert concept(learner)["status"] == "weak"
    session.scalars(
        select(Question).where(Question.id == "w01-l01-q02")
    ).one().retired_reason = "Old."
    session.commit()
    assert concept(learner)["status"] == "insufficient"
    assert concept(learner)["active_questions"] == 1


def test_recovery_resets_after_a_new_recorded_miss_and_expiration_is_distinct(
    learner: TestClient, clock: FakeClock
) -> None:
    answer_wrong(learner, "w01-l01-q01")
    answer_wrong(learner, "w01-l01-q02")
    for day in (4, 5, 6):
        clock.set(datetime(2026, 10, day, 10, tzinfo=UTC))
        answer_right(learner, "w01-l01-q01")
        answer_right(learner, "w01-l01-q02")
    assert concept(learner)["status"] == "recovered"
    clock.set(datetime(2026, 10, 9, 10, tzinfo=UTC))
    answer_wrong(learner, "w01-l01-q01")
    assert concept(learner)["status"] == "weak"
    assert concept(learner)["recovery_days"] == 0
    clock.set(datetime(2026, 11, 9, 10, tzinfo=UTC))
    assert concept(learner)["status"] == "expired"


def test_evidence_is_private_scoped_to_active_stacks_and_preserved_on_reactivation(
    session: Session,
    learner: TestClient,
    admin: TestClient,
    signed_in: ClientFactory,
    make_content: ContentFactory,
) -> None:
    import_folder(session, make_content(other_stack))
    answer_wrong(learner, "w01-l01-q01")
    answer_wrong(learner, "w01-l01-q02")
    admin.post("/invitations", json={"email": "other@example.com"}).raise_for_status()
    other = signed_in("other@example.com")
    onboard(other)
    assert concept(other)["recent_missed_questions"] == 0
    onboard(learner, "other-stack")
    assert learner.get(URL).status_code == 409
    other_evidence = learner.get("/stacks/other-stack/concept-evidence").json()
    assert all(c["recent_missed_questions"] == 0 for c in other_evidence["concepts"])
    onboard(learner, "mini-stack")
    assert concept(learner)["status"] == "weak"


def test_challenge_replays_and_ungraded_first_answers_are_not_guidance_evidence(
    session: Session,
    api: TestClient,
    make_content: ContentFactory,
    clock: FakeClock,
    grader: FakeGrader,
) -> None:
    clock.set(MORNING)
    import_stack(session, make_content)
    onboard(api)
    today(api)
    challenge_answer(api, MC1, "a").raise_for_status()
    challenge_answer(api, MC2, "a").raise_for_status()
    grader.failing = True
    challenge_answer(api, WRITTEN, "A supplied answer.").raise_for_status()
    assert concept(api, "concept-d")["latest_miss"] is None
    grader.failing = False
    challenge_answer(api, MC1, "b").raise_for_status()
    assert concept(api)["recent_missed_questions"] == 0


def test_lesson_quiz_and_retake_outcomes_contribute_to_the_same_concept(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    clock.set(datetime(2026, 10, 3, 10, tzinfo=UTC))
    import_folder(session, make_content())
    onboard(api)
    _, result = pass_missing_one(api)
    [retake] = result["retakes"]
    assert concept(api)["recent_missed_questions"] == 1
    answer_retake(api, retake, "b").raise_for_status()
    assert concept(api)["status"] == "weak"
    assert concept(api)["recent_missed_questions"] == 2


def test_removed_teaching_lessons_are_not_linked(learner: TestClient, session: Session) -> None:
    # Question tags can survive a Syllabus removing or moving their teaching Lesson.
    for question in session.scalars(select(Question).where(Question.concept.has(id="concept-a"))):
        question.lesson_id = "removed-lesson"
    session.commit()
    assert concept(learner)["lesson_id"] is None
    assert concept(learner)["lesson_title"] is None
