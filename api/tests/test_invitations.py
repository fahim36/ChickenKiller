"""Invite-only sign-in: the Admin invites an email, and that person becomes a Learner."""

from fastapi.testclient import TestClient

from tests.conftest import ADMIN_EMAIL, ClientFactory

ADA = "ada@example.com"


def pending(admin: TestClient) -> list[str]:
    response = admin.get("/invitations")
    assert response.status_code == 200
    return [invitation["email"] for invitation in response.json()]


def test_the_admin_is_let_in_without_an_invitation(admin: TestClient) -> None:
    me = admin.get("/me").json()
    assert (me["email"], me["is_admin"]) == (ADMIN_EMAIL, True)


def test_an_invited_email_is_pending(admin: TestClient) -> None:
    response = admin.post("/invitations", json={"email": ADA})

    assert response.status_code == 201
    assert response.json()["email"] == ADA
    assert pending(admin) == [ADA]


def test_pending_invitations_are_listed_oldest_first(admin: TestClient) -> None:
    for email in ["b@example.com", "a@example.com"]:
        admin.post("/invitations", json={"email": email})

    assert pending(admin) == ["b@example.com", "a@example.com"]


def test_an_invited_person_becomes_a_learner_on_first_sign_in(
    admin: TestClient, signed_in: ClientFactory
) -> None:
    admin.post("/invitations", json={"email": ADA})

    response = signed_in(ADA).get("/me")

    assert response.status_code == 200
    assert (response.json()["email"], response.json()["is_admin"]) == (ADA, False)
    assert pending(admin) == []


def test_a_learner_keeps_access_after_their_first_sign_in(
    admin: TestClient, signed_in: ClientFactory
) -> None:
    admin.post("/invitations", json={"email": ADA})
    ada = signed_in(ADA)
    ada.get("/me")

    assert ada.get("/me").status_code == 200
    assert ada.get("/stacks").status_code == 200


def test_invitations_ignore_letter_case(admin: TestClient, signed_in: ClientFactory) -> None:
    admin.post("/invitations", json={"email": "  Ada@Example.COM "})

    assert pending(admin) == [ADA]
    assert signed_in("ada@EXAMPLE.com").get("/me").json()["email"] == ADA


def test_a_person_who_was_not_invited_is_refused(signed_in: ClientFactory) -> None:
    response = signed_in("stranger@example.com").get("/stacks")

    assert response.status_code == 403
    assert response.json()["detail"] == {
        "code": "not_invited",
        "message": "This email address hasn't been invited. Ask the Admin for an invitation.",
    }


def test_a_learner_cannot_see_or_send_invitations(api: TestClient) -> None:
    assert api.get("/invitations").status_code == 403
    assert api.post("/invitations", json={"email": ADA}).status_code == 403


def test_the_same_email_cannot_be_invited_twice(admin: TestClient) -> None:
    admin.post("/invitations", json={"email": ADA})

    response = admin.post("/invitations", json={"email": ADA.upper()})

    assert response.status_code == 409
    assert response.json()["detail"] == "ada@example.com is already invited."


def test_a_learner_cannot_be_invited(admin: TestClient) -> None:
    response = admin.post("/invitations", json={"email": ADMIN_EMAIL})

    assert response.status_code == 409
    assert response.json()["detail"] == "admin@example.com is already a Learner."


def test_an_invitation_needs_an_email_address(admin: TestClient) -> None:
    assert admin.post("/invitations", json={"email": "not an email"}).status_code == 422
    assert pending(admin) == []
