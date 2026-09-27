"""The Week map: Lessons with their lock states and Milestones with their ticks (#5)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from tests.conftest import (
    LEARNER_EMAIL,
    ClientFactory,
    ContentFactory,
    complete_lessons,
    make_bank,
    onboard,
)

WEEK_MAP = "/stacks/mini-stack"


def two_weeks(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    """The mini Stack plus a second Week: w01-l01, w01-l02, then w02-l01."""
    syllabus["weeks"].append(
        {
            "id": "w02",
            "number": 2,
            "title": "Week two",
            "goal": "Learn more.",
            "deliverable": "Another thing.",
            "interview_checks": [],
            "lessons": [
                {
                    "id": "w02-l01",
                    "title": "Third lesson",
                    "topics": ["Topic D"],
                    "exercise": None,
                    "minutes": 45,
                    "materials": [],
                }
            ],
            "milestones": [
                {
                    "id": "w02-m01",
                    "title": "Apply somewhere",
                    "kind": "job-hunt",
                    "minutes": 30,
                    "materials": [],
                },
                {
                    "id": "w02-m02",
                    "title": "Ship it",
                    "kind": "build",
                    "minutes": 90,
                    "materials": [],
                },
            ],
        }
    )


def other_stack(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    """The mini Stack's content under another Stack, so its IDs are the same."""
    syllabus["stack"] = {"id": "other-stack", "name": "Other Stack", "summary": "Another one."}


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory
) -> Iterator[TestClient]:
    """A new Learner onboarded onto a two-Week mini Stack, where every Lesson has a Question
    Bank."""
    banks = {"w01-l02": make_bank("w01-l02", "second"), "w02-l01": make_bank("w02-l01", "third")}
    import_folder(session, make_content(two_weeks, extra_banks=banks))
    onboard(api)
    yield api


def lesson_states(client: TestClient) -> dict[str, str]:
    weeks = client.get(WEEK_MAP).json()["weeks"]
    return {lesson["id"]: lesson["state"] for week in weeks for lesson in week["lessons"]}


def test_the_week_map_lists_lessons_and_milestones_under_their_weeks_in_order(
    learner: TestClient,
) -> None:
    weeks = learner.get(WEEK_MAP).json()["weeks"]

    assert [
        (w["id"], [lesson["id"] for lesson in w["lessons"]], [m["id"] for m in w["milestones"]])
        for w in weeks
    ] == [
        ("w01", ["w01-l01", "w01-l02"], ["w01-m01"]),
        ("w02", ["w02-l01"], ["w02-m01", "w02-m02"]),
    ]


def test_a_new_learner_has_only_the_first_lesson_unlocked(learner: TestClient) -> None:
    assert lesson_states(learner) == {
        "w01-l01": "unlocked",
        "w01-l02": "locked",
        "w02-l01": "locked",
    }


def test_a_new_learner_has_no_milestone_ticked(learner: TestClient) -> None:
    weeks = learner.get(WEEK_MAP).json()["weeks"]

    assert [m["ticked"] for w in weeks for m in w["milestones"]] == [False, False, False]


def test_completing_a_lesson_unlocks_the_next_one_on_the_week_map(
    session: Session, learner: TestClient
) -> None:
    complete_lessons(session, "w01-l01", "w01-l02")

    assert lesson_states(learner) == {
        "w01-l01": "completed",
        "w01-l02": "completed",
        "w02-l01": "unlocked",
    }


def test_the_lesson_page_shows_its_state_and_a_locked_lesson_can_still_be_read(
    learner: TestClient,
) -> None:
    unlocked = learner.get("/stacks/mini-stack/lessons/w01-l01")
    locked = learner.get("/stacks/mini-stack/lessons/w02-l01")

    assert (unlocked.status_code, unlocked.json()["state"]) == (200, "unlocked")
    assert (locked.status_code, locked.json()["state"]) == (200, "locked")
    assert locked.json()["title"] == "Third lesson"


# --- Milestones ------------------------------------------------------------------------------


def tick(client: TestClient, milestone_id: str, ticked: bool = True) -> Response:
    return client.put(f"/stacks/mini-stack/milestones/{milestone_id}", json={"ticked": ticked})


def ticked_milestones(client: TestClient, stack_id: str = "mini-stack") -> list[str]:
    weeks = client.get(f"/stacks/{stack_id}").json()["weeks"]
    return [m["id"] for w in weeks for m in w["milestones"] if m["ticked"]]


def test_a_ticked_milestone_is_saved_and_survives_a_reload(
    learner: TestClient, signed_in: ClientFactory
) -> None:
    response = tick(learner, "w02-m01")

    assert (response.status_code, response.json()) == (200, {"id": "w02-m01", "ticked": True})
    assert ticked_milestones(signed_in(LEARNER_EMAIL)) == ["w02-m01"]


def test_a_milestone_can_be_unticked(learner: TestClient) -> None:
    tick(learner, "w01-m01")
    tick(learner, "w02-m02")

    response = tick(learner, "w01-m01", ticked=False)

    assert response.json() == {"id": "w01-m01", "ticked": False}
    assert ticked_milestones(learner) == ["w02-m02"]


def test_ticking_twice_or_unticking_an_unticked_milestone_changes_nothing(
    learner: TestClient,
) -> None:
    tick(learner, "w01-m01")
    tick(learner, "w01-m01")
    tick(learner, "w02-m01", ticked=False)

    assert ticked_milestones(learner) == ["w01-m01"]


def test_ticking_milestones_does_not_change_any_lock_state(
    session: Session, learner: TestClient
) -> None:
    complete_lessons(session, "w01-l01")
    before = lesson_states(learner)

    for milestone in ["w01-m01", "w02-m01", "w02-m02"]:
        tick(learner, milestone)

    assert before == {"w01-l01": "completed", "w01-l02": "unlocked", "w02-l01": "locked"}
    assert lesson_states(learner) == before


def test_milestone_ticks_are_kept_per_learner(
    learner: TestClient, admin: TestClient, signed_in: ClientFactory
) -> None:
    admin.post("/invitations", json={"email": "other@example.com"}).raise_for_status()
    other = signed_in("other@example.com")
    onboard(other)

    tick(learner, "w01-m01")

    assert ticked_milestones(other) == []


def test_milestone_ticks_are_kept_per_stack(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content(other_stack))
    tick(learner, "w01-m01")

    onboard(learner, "other-stack")
    assert ticked_milestones(learner, "other-stack") == []
    onboard(learner, "mini-stack")
    assert ticked_milestones(learner) == ["w01-m01"]


def test_an_unknown_milestone_cannot_be_ticked(learner: TestClient) -> None:
    assert tick(learner, "w09-m99").status_code == 404


def test_only_the_active_stacks_milestones_can_be_ticked(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content(other_stack))
    onboard(learner, "other-stack")

    response = tick(learner, "w01-m01")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "not_active_stack"


# --- The Lesson Quiz guard -------------------------------------------------------------------
# These only tell "refused" from "let through"; the quiz itself is tested in test_lesson_quiz.py.


def start_quiz(client: TestClient, lesson_id: str, stack_id: str = "mini-stack") -> Response:
    return client.post(f"/stacks/{stack_id}/lessons/{lesson_id}/quiz")


def refusal(response: Response) -> tuple[int, str]:
    if response.status_code == 200:
        return LET_THROUGH
    return response.status_code, response.json()["detail"]["code"]


LET_THROUGH = (200, "started")


def test_the_unlocked_lessons_quiz_can_be_started(learner: TestClient) -> None:
    assert refusal(start_quiz(learner, "w01-l01")) == LET_THROUGH


def test_a_locked_lessons_quiz_is_refused(learner: TestClient) -> None:
    assert refusal(start_quiz(learner, "w01-l02")) == (409, "lesson_locked")
    assert refusal(start_quiz(learner, "w02-l01")) == (409, "lesson_locked")


def test_completing_a_lesson_lets_the_next_lessons_quiz_start(
    session: Session, learner: TestClient
) -> None:
    complete_lessons(session, "w01-l01")

    assert refusal(start_quiz(learner, "w01-l02")) == LET_THROUGH
    assert refusal(start_quiz(learner, "w02-l01")) == (409, "lesson_locked")


def test_a_completed_lessons_quiz_is_refused(session: Session, learner: TestClient) -> None:
    complete_lessons(session, "w01-l01")

    assert refusal(start_quiz(learner, "w01-l01")) == (409, "lesson_completed")


def test_ticking_every_milestone_unlocks_no_quiz(learner: TestClient) -> None:
    for milestone in ["w01-m01", "w02-m01", "w02-m02"]:
        tick(learner, milestone)

    assert refusal(start_quiz(learner, "w01-l02")) == (409, "lesson_locked")


def test_only_the_active_stacks_quizzes_can_be_started(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content(other_stack))
    onboard(learner, "other-stack")

    assert refusal(start_quiz(learner, "w01-l01")) == (409, "not_active_stack")
    assert refusal(start_quiz(learner, "w01-l01", "other-stack")) == LET_THROUGH


def test_an_unknown_lessons_quiz_is_not_found(learner: TestClient) -> None:
    assert start_quiz(learner, "w09-l99").status_code == 404
