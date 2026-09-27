"""Every endpoint except the health check needs a valid Clerk session token."""

import time
from collections.abc import Callable, Iterator, Sequence

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.routing import BaseRoute

from tests.conftest import ADMIN_EMAIL, TokenFactory

PROTECTED = ["/me", "/stacks", "/stacks/mini-stack", "/invitations"]


def test_health_needs_no_sign_in(anonymous: TestClient) -> None:
    assert anonymous.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("path", PROTECTED)
def test_a_request_without_a_token_is_refused(anonymous: TestClient, path: str) -> None:
    response = anonymous.get(path)

    assert response.status_code == 401
    assert response.json()["detail"] == "Sign in first."


def api_routes(routes: Sequence[BaseRoute], prefix: str = "") -> Iterator[tuple[str, APIRoute]]:
    """Every API route with its prefix, looking inside included routers (which FastAPI keeps as
    one entry each, holding the original router)."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield prefix, route
        elif (router := getattr(route, "original_router", None)) is not None:
            yield from api_routes(router.routes, prefix + route.include_context.prefix)  # type: ignore[attr-defined]


def test_every_route_but_the_health_check_refuses_a_request_without_a_token(
    app: FastAPI, anonymous: TestClient
) -> None:
    """Walks the whole app, so a new route can't be left open by mistake. Path parameters are
    filled with a placeholder and bodies left empty: the sign-in check comes first."""
    checked, open_routes = 0, []
    for prefix, route in api_routes(app.routes):
        if route.path == "/health":
            continue
        path = prefix + route.path_format
        for name in route.param_convertors:
            path = path.replace("{" + name + "}", "00000000-0000-0000-0000-000000000000")
        for method in route.methods or ():
            response = anonymous.request(method, path, json={})
            checked += 1
            if response.status_code != 401:
                open_routes.append(f"{method} {route.path}: {response.status_code}")

    assert open_routes == []
    assert checked >= 20  # every route of the main router


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
