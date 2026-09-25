import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

LOCAL_DATABASE_URL = "postgresql+psycopg://learning:learning@localhost:5433/learning"


def normalize_database_url(url: str) -> str:
    """Hosts such as Render hand out `postgres://` URLs; SQLAlchemy needs the driver named."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def env_list(name: str) -> frozenset[str]:
    """A comma-separated environment variable, as a set of non-empty entries."""
    return frozenset(item.strip() for item in os.environ.get(name, "").split(",") if item.strip())


DATABASE_URL = normalize_database_url(os.environ.get("DATABASE_URL", LOCAL_DATABASE_URL))

# Sign-in (docs/deploy.md). CLERK_ISSUER is the Clerk instance's Frontend API URL, such as
# https://your-app.clerk.accounts.dev. Without it every endpoint but /health answers 503.
CLERK_ISSUER = os.environ.get("CLERK_ISSUER", "").rstrip("/")
CLERK_JWKS_URL = os.environ.get("CLERK_JWKS_URL") or (
    f"{CLERK_ISSUER}/.well-known/jwks.json" if CLERK_ISSUER else ""
)
# The web app's origins, such as https://learning-web-abcd.onrender.com,http://localhost:3000
CLERK_AUTHORIZED_PARTIES = env_list("CLERK_AUTHORIZED_PARTIES")
ADMIN_EMAILS = frozenset(email.lower() for email in env_list("ADMIN_EMAILS"))

CONTENT_DIR = Path(os.environ.get("CONTENT_DIR", REPO_ROOT / "content"))
CONTENT_SCHEMA_DIR = Path(os.environ.get("CONTENT_SCHEMA_DIR", CONTENT_DIR / "schema"))
