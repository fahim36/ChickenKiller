"""Lesson fingerprints hash only the Lesson's own content

Revision ID: 0015_lesson_fingerprints
Revises: 0014_challenge_plays
Create Date: 2026-09-27 22:00:00.000000

- `lessons.content_hash`: now the Lesson's fields and Week only; the Questions tagged to it are
  compared through `lessons.question_ids`, so a Question that only left a Lesson no longer makes
  it Updated. The old hashes mixed both, so they are cleared here; the release step imports
  every version on each deploy, and an unchanged import fills them in again. Until then every
  Lesson is taken as unchanged.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015_lesson_fingerprints"
down_revision: str | Sequence[str] | None = "0014_challenge_plays"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_COMMENT = (
    "The Lesson's content as content-diff compares it (fields, Week). Equal across "
    "versions means its own content is unchanged."
)
OLD_COMMENT = (
    "The Lesson's content as content-diff compares it (fields, Week), plus question_ids. "
    "Equal across versions means unchanged."
)


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE lessons SET content_hash = NULL")
    op.alter_column(
        "lessons",
        "content_hash",
        existing_type=sa.String(length=64),
        existing_nullable=True,
        comment=NEW_COMMENT,
        existing_comment=OLD_COMMENT,
    )


def downgrade() -> None:
    """Downgrade schema. The old hashes can't be rebuilt, so they stay cleared."""
    op.execute("UPDATE lessons SET content_hash = NULL")
    op.alter_column(
        "lessons",
        "content_hash",
        existing_type=sa.String(length=64),
        existing_nullable=True,
        comment=OLD_COMMENT,
        existing_comment=NEW_COMMENT,
    )
