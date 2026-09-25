"""Checking Clerk session tokens (ADR-0002: sign-in is handed to Clerk).

The web app sends the signed-in person's Clerk session token on every request, as
`Authorization: Bearer <token>`. A token is accepted only if:

- it is an RS256 JWT signed by one of our Clerk instance's keys (its published JWKS);
- `iss` is our Clerk instance, and `azp` (the site the token was issued to) is one of ours;
- it is inside its `nbf`..`exp` window (Clerk tokens live 60 s), allowing 5 s of clock skew;
- it has `sub` (the Clerk user id) and `email`.

Clerk session tokens carry no email by default. Our Clerk instance adds it as a custom
session-token claim, `{"email": "{{user.primary_email_address}}"}` (docs/deploy.md). That keeps
each request free of calls to Clerk's Backend API, and the API needs no Clerk secret key.
"""

from dataclasses import dataclass
from typing import Any, Protocol

import jwt

from app import config

CLOCK_SKEW_SECONDS = 5


@dataclass(frozen=True)
class AuthSettings:
    issuer: str
    jwks_url: str
    # Empty means any `azp` is accepted. Production sets the web app's origin.
    authorized_parties: frozenset[str]
    # Lower-cased. The Admin is always let in, invited or not.
    admin_emails: frozenset[str]


class KeySource(Protocol):
    """Where the public keys that sign session tokens come from."""

    def signing_key(self, token: str) -> Any:
        """The public key that should have signed `token`, chosen by its `kid` header."""
        ...


class ClerkJwks:
    """The keys Clerk publishes at `<issuer>/.well-known/jwks.json`, fetched once and cached."""

    def __init__(self, url: str) -> None:
        self._client = jwt.PyJWKClient(url, cache_keys=True, timeout=10)

    def signing_key(self, token: str) -> Any:
        return self._client.get_signing_key_from_jwt(token).key


@dataclass(frozen=True)
class Identity:
    """Who a valid session token says is signed in."""

    clerk_user_id: str
    email: str  # lower-cased


class InvalidToken(Exception):
    pass


class KeysUnavailable(Exception):
    """Clerk's JWKS could not be fetched, so no token can be checked right now."""


class TokenVerifier:
    def __init__(self, settings: AuthSettings, keys: KeySource) -> None:
        self.settings = settings
        self._keys = keys

    @classmethod
    def from_config(cls) -> "TokenVerifier | None":
        """The verifier for the environment's Clerk instance, or None if CLERK_ISSUER isn't set."""
        if not config.CLERK_ISSUER:
            return None
        settings = AuthSettings(
            issuer=config.CLERK_ISSUER,
            jwks_url=config.CLERK_JWKS_URL,
            authorized_parties=config.CLERK_AUTHORIZED_PARTIES,
            admin_emails=config.ADMIN_EMAILS,
        )
        return cls(settings, ClerkJwks(settings.jwks_url))

    def verify(self, token: str) -> Identity:
        try:
            claims = jwt.decode(
                token,
                self._keys.signing_key(token),
                algorithms=["RS256"],
                issuer=self.settings.issuer,
                leeway=CLOCK_SKEW_SECONDS,
                options={"require": ["exp", "iat", "iss", "sub"]},
            )
        except jwt.PyJWKClientConnectionError as error:
            raise KeysUnavailable(str(error)) from error
        except jwt.PyJWTError as error:
            raise InvalidToken(str(error)) from error

        parties = self.settings.authorized_parties
        if parties and claims.get("azp") not in parties:
            raise InvalidToken("Token was issued to another site")
        email = claims.get("email")
        if not isinstance(email, str) or not email.strip():
            raise InvalidToken("Token has no email claim; see docs/deploy.md")
        return Identity(clerk_user_id=claims["sub"], email=email.strip().lower())
