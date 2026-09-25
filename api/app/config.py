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


DATABASE_URL = normalize_database_url(os.environ.get("DATABASE_URL", LOCAL_DATABASE_URL))
CONTENT_DIR = Path(os.environ.get("CONTENT_DIR", REPO_ROOT / "content"))
CONTENT_SCHEMA_DIR = Path(os.environ.get("CONTENT_SCHEMA_DIR", CONTENT_DIR / "schema"))
