import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://learning:learning@localhost:5432/learning"
)
CONTENT_SCHEMA_DIR = Path(os.environ.get("CONTENT_SCHEMA_DIR", REPO_ROOT / "content" / "schema"))
