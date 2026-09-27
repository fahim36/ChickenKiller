"""Onboarding: a Learner activates one or more Stacks, and changes them later in settings (#4).

There is no time zone step: every Day is a UTC Day (ADR-0005).
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from tests.conftest import (
    LEARNER_EMAIL,
    ClientFactory,
    ContentFactory,
    complete_lessons,
    make_changelog,
)


def other_stack(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    syllabus["stack"] = {"id": "other-stack", "name": "Other Stack", "summary": "Another one."}


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory
) -> Iterator[TestClient]:
    """A newly invited Learner, with two Stacks published: the mini Stack and another."""
    import_folder(session, make_content())
    import_folder(session, make_content(other_stack))
    yield api


def activate(client: TestClient, *stack_ids: str) -> Response:
    """Save the Learner's Active Stacks, as onboarding and settings do."""
    return client.put("/me/active-stacks", json={"stack_ids": list(stack_ids)})


def active_ids(me: dict[str, Any]) -> list[str]:
    return [s["id"] for s in me["active_stacks"]]


def test_a_first_sign_in_needs_onboarding(learner: TestClient) -> None:
    me = learner.get("/me").json()

    assert me["needs_onboarding"] is True
    assert me["active_stacks"] == []
    assert "time_zone" not in me


def test_onboarding_activates_one_stack(learner: TestClient) -> None:
    response = activate(learner, "mini-stack")

    assert response.status_code == 200
    me = learner.get("/me").json()
    assert me["needs_onboarding"] is False
    assert [(s["id"], s["name"]) for s in me["active_stacks"]] == [("mini-stack", "Mini Stack")]
    assert response.json() == me


def test_onboarding_activates_several_stacks(learner: TestClient) -> None:
    me = activate(learner, "mini-stack", "other-stack").json()

    assert me["needs_onboarding"] is False
    assert sorted(active_ids(me)) == ["mini-stack", "other-stack"]
    for stack_id in ["mini-stack", "other-stack"]:
        assert learner.get(f"/stacks/{stack_id}").status_code == 200


def test_naming_a_stack_twice_activates_it_once(learner: TestClient) -> None:
    assert active_ids(activate(learner, "mini-stack", "mini-stack").json()) == ["mini-stack"]


def test_at_least_one_stack_must_be_picked(learner: TestClient) -> None:
    response = activate(learner)

    assert response.status_code == 422
    assert response.json()["detail"] == "Pick at least one Stack."
    assert learner.get("/me").json()["needs_onboarding"] is True


def test_a_returning_learner_does_not_need_onboarding(
    learner: TestClient, signed_in: ClientFactory
) -> None:
    activate(learner, "mini-stack", "other-stack")

    again = signed_in(LEARNER_EMAIL).get("/me").json()

    assert again["needs_onboarding"] is False
    assert sorted(active_ids(again)) == ["mini-stack", "other-stack"]


def test_settings_can_activate_another_stack(learner: TestClient) -> None:
    started = activate(learner, "mini-stack").json()["active_stacks"][0]

    me = activate(learner, "mini-stack", "other-stack").json()

    assert sorted(active_ids(me)) == ["mini-stack", "other-stack"]
    assert next(s for s in me["active_stacks"] if s["id"] == "mini-stack") == started


def test_a_deactivated_stack_is_no_longer_studied(learner: TestClient) -> None:
    activate(learner, "mini-stack", "other-stack")

    me = activate(learner, "other-stack").json()

    assert active_ids(me) == ["other-stack"]
    response = learner.get("/stacks/mini-stack")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "not_active_stack"


def test_deactivating_then_reactivating_a_stack_keeps_its_progress(
    session: Session, learner: TestClient
) -> None:
    started = activate(learner, "mini-stack", "other-stack").json()["active_stacks"]
    complete_lessons(session, "w01-l01")
    learner.put("/stacks/mini-stack/milestones/w01-m01", json={"ticked": True})

    activate(learner, "other-stack")
    back = activate(learner, "mini-stack", "other-stack").json()

    assert sorted(back["active_stacks"], key=lambda s: s["id"]) == sorted(
        started, key=lambda s: s["id"]
    )
    week_map = learner.get("/stacks/mini-stack").json()
    lessons = {lesson["id"]: lesson["state"] for w in week_map["weeks"] for lesson in w["lessons"]}
    assert (lessons["w01-l01"], lessons["w01-l02"]) == ("completed", "unlocked")
    ticked = [m["id"] for w in week_map["weeks"] for m in w["milestones"] if m["ticked"]]
    assert ticked == ["w01-m01"]


def unpublished(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    syllabus["stack"] = {
        "id": "draft-stack",
        "name": "Draft Stack",
        "summary": "Not ready yet.",
        "published": False,
    }


def test_only_published_stacks_are_listed(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content(unpublished))

    assert [s["id"] for s in learner.get("/stacks").json()] == ["mini-stack", "other-stack"]


@pytest.mark.parametrize("stack_id", ["draft-stack", "no-such-stack"])
def test_only_published_stacks_can_be_activated(
    session: Session, learner: TestClient, make_content: ContentFactory, stack_id: str
) -> None:
    import_folder(session, make_content(unpublished))

    response = activate(learner, "mini-stack", stack_id)

    assert response.status_code == 422
    assert response.json()["detail"] == "Choose one of the published Stacks."
    assert learner.get("/me").json()["needs_onboarding"] is True


# Withdrawing a Stack changes no Lesson, so its changelog lists no changes.
WITHDRAWN_CHANGELOG = make_changelog("v2026-02-01", "v2026-01-01")


def withdrawn(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    syllabus["version"] = "v2026-02-01"
    syllabus["stack"]["published"] = False


def test_a_newer_version_can_unpublish_a_stack(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content(withdrawn, changelog=WITHDRAWN_CHANGELOG))

    assert [s["id"] for s in learner.get("/stacks").json()] == ["other-stack"]


def test_a_learner_keeps_a_withdrawn_active_stack(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    started = activate(learner, "mini-stack").json()["active_stacks"]
    import_folder(session, make_content(withdrawn, changelog=WITHDRAWN_CHANGELOG))

    response = activate(learner, "mini-stack", "other-stack")

    assert response.status_code == 200
    assert started[0] in response.json()["active_stacks"]
    assert learner.get("/stacks/mini-stack").status_code == 200


def test_a_withdrawn_stack_once_deactivated_cannot_be_reactivated(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    activate(learner, "mini-stack", "other-stack")
    import_folder(session, make_content(withdrawn, changelog=WITHDRAWN_CHANGELOG))
    activate(learner, "other-stack")

    response = activate(learner, "mini-stack", "other-stack")

    assert response.status_code == 422
    assert active_ids(learner.get("/me").json()) == ["other-stack"]


@pytest.mark.parametrize("path", ["/stacks/mini-stack", "/stacks/mini-stack/lessons/w01-l01"])
def test_onboarding_is_required_before_any_syllabus_or_lesson(
    learner: TestClient, path: str
) -> None:
    response = learner.get(path)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "onboarding_needed"
    activate(learner, "mini-stack")
    assert learner.get(path).status_code == 200


def test_the_stack_list_is_open_before_onboarding(learner: TestClient) -> None:
    assert learner.get("/stacks").status_code == 200
