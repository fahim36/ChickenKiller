"""Every endpoint except the health check needs a valid Clerk session token."""

import time
from collections.abc import Callable

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from tests.conftest import ADMIN_EMAIL, TokenFactory

PROTECTED = ["/me", "/stacks", "/stacks/mini-stack", "/invitations"]


def test_health_needs_no_sign_in(anonymous: TestClient) -> None:
    assert anonymous.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("path", PROTECTED)
def test_a_request_without_a_token_is_refused(anonymous: TestClient, path: str) -> None:
    response = anonymous.get(path)

    assert response.status_code == 401
    assert response.json()["detail"] == "Sign in first."


def test_a_valid_token_is_accepted(anonymous: TestClient, make_token: TokenFactory) -> None:
    response = anonymous.get("/me", headers={"Authorization": f"Bearer {make_token(ADMIN_EMAIL)}"})

    assert response.status_code == 200
    assert response.json()["email"] == ADMIN_EMAIL


STRANGER = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# Each makes a bad token from `make_token` and the current Unix time.
BAD_TOKENS: dict[str, Callable[[TokenFactory, int], str]] = {
    "not a JWT": lambda make, now: "not-a-token",
    "signed by another key": lambda make, now: make(ADMIN_EMAIL, key=STRANGER),
    "expired": lambda make, now: make(ADMIN_EMAIL, iat=now - 600, nbf=now - 600, exp=now - 60),
    "not valid yet": lambda make, now: make(ADMIN_EMAIL, nbf=now + 600),
    "from another Clerk instance": lambda make, now: make(ADMIN_EMAIL, iss="https://evil.example"),
    "issued to another site": lambda make, now: make(ADMIN_EMAIL, azp="https://evil.example"),
    "without an email claim": lambda make, now: make(None),
}


@pytest.mark.parametrize("case", BAD_TOKENS)
def test_an_invalid_token_is_refused(
    anonymous: TestClient, make_token: TokenFactory, case: str
) -> None:
    token = BAD_TOKENS[case](make_token, int(time.time()))

    response = anonymous.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Your sign-in is invalid or has expired."
