"""Onboarding: a Learner picks an Active Stack and confirms their time zone (#4)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from tests.conftest import LEARNER_EMAIL, ClientFactory, ContentFactory


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


def choose(
    client: TestClient, stack_id: str = "mini-stack", time_zone: str = "Asia/Dhaka"
) -> Response:
    return client.put("/me/settings", json={"active_stack_id": stack_id, "time_zone": time_zone})


def test_a_first_sign_in_needs_onboarding(learner: TestClient) -> None:
    me = learner.get("/me").json()

    assert me["needs_onboarding"] is True
    assert (me["active_stack"], me["time_zone"]) == (None, None)


def test_onboarding_sets_the_active_stack_and_time_zone(learner: TestClient) -> None:
    response = choose(learner)

    assert response.status_code == 200
    me = learner.get("/me").json()
    assert me["needs_onboarding"] is False
    assert (me["active_stack"]["id"], me["active_stack"]["name"]) == ("mini-stack", "Mini Stack")
    assert me["time_zone"] == "Asia/Dhaka"
    assert response.json() == me


@pytest.mark.parametrize("time_zone", ["UTC", "America/Los_Angeles", "Asia/Calcutta"])
def test_any_iana_time_zone_is_accepted(learner: TestClient, time_zone: str) -> None:
    assert choose(learner, time_zone=time_zone).status_code == 200
    assert learner.get("/me").json()["time_zone"] == time_zone


@pytest.mark.parametrize("time_zone", ["", "Mars/Olympus_Mons", "asia/dhaka", "GMT+6", "../etc"])
def test_a_time_zone_that_is_not_an_iana_name_is_refused(
    learner: TestClient, time_zone: str
) -> None:
    response = choose(learner, time_zone=time_zone)

    assert response.status_code == 422
    assert "time zone" in str(response.json()["detail"])
    assert learner.get("/me").json()["needs_onboarding"] is True


def test_a_returning_learner_does_not_need_onboarding(
    learner: TestClient, signed_in: ClientFactory
) -> None:
    choose(learner)

    again = signed_in(LEARNER_EMAIL).get("/me").json()

    assert again["needs_onboarding"] is False
    assert again["active_stack"]["id"] == "mini-stack"


def test_switching_the_active_stack_keeps_the_record_on_the_previous_one(
    learner: TestClient,
) -> None:
    started = choose(learner, "mini-stack").json()["active_stack"]

    switched = choose(learner, "other-stack").json()
    back = choose(learner, "mini-stack").json()

    assert switched["active_stack"]["id"] == "other-stack"
    assert switched["active_stack"]["started_at"] != started["started_at"]
    assert back["active_stack"] == started


def test_settings_can_change_the_time_zone_alone(learner: TestClient) -> None:
    started = choose(learner, time_zone="Asia/Dhaka").json()["active_stack"]

    me = choose(learner, time_zone="Europe/Berlin").json()

    assert (me["time_zone"], me["active_stack"]) == ("Europe/Berlin", started)


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
def test_only_a_published_stack_can_be_chosen(
    session: Session, learner: TestClient, make_content: ContentFactory, stack_id: str
) -> None:
    import_folder(session, make_content(unpublished))

    response = choose(learner, stack_id)

    assert response.status_code == 422
    assert response.json()["detail"] == "Choose one of the published Stacks."
    assert learner.get("/me").json()["needs_onboarding"] is True


def test_a_newer_version_can_unpublish_a_stack(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    def withdrawn(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["version"] = "v2026-02-01"
        syllabus["stack"]["published"] = False

    import_folder(session, make_content(withdrawn))

    assert [s["id"] for s in learner.get("/stacks").json()] == ["other-stack"]


def test_a_learner_on_a_withdrawn_stack_keeps_it_and_can_change_their_time_zone(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    started = choose(learner).json()["active_stack"]

    def withdrawn(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["version"] = "v2026-02-01"
        syllabus["stack"]["published"] = False

    import_folder(session, make_content(withdrawn))
    response = choose(learner, "mini-stack", time_zone="Europe/Berlin")

    assert response.status_code == 200
    assert (response.json()["active_stack"], response.json()["time_zone"]) == (
        started,
        "Europe/Berlin",
    )


@pytest.mark.parametrize("path", ["/stacks/mini-stack", "/stacks/mini-stack/lessons/w01-l01"])
def test_onboarding_is_required_before_any_syllabus_or_lesson(
    learner: TestClient, path: str
) -> None:
    response = learner.get(path)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "onboarding_needed"
    choose(learner)
    assert learner.get(path).status_code == 200


def test_the_stack_list_is_open_before_onboarding(learner: TestClient) -> None:
    assert learner.get("/stacks").status_code == 200
