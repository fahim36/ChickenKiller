"""updated lessons (#13)

Revision ID: 0009_updated_lessons
Revises: 0008
Create Date: 2026-09-26 20:00:00.000000

- `lessons.content_hash`: each Lesson's content as content-diff compares it. Lessons imported
  before this migration have none until their version is imported again (the release step
  imports every version on each deploy, and an unchanged import fills it in).
- `completed_lessons.syllabus_version`: the version each Lesson was completed in. Existing rows
  get the version of the Lesson's last passed Lesson Quiz, or else the Stack's current version.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_updated_lessons"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "lessons",
        sa.Column(
            "content_hash",
            sa.String(length=64),
            nullable=True,
            comment=(
                "The Lesson's content as content-diff compares it (fields, Week, Question "
                "Bank). Equal across versions means unchanged."
            ),
        ),
    )
    op.add_column(
        "completed_lessons",
        sa.Column(
            "syllabus_version",
            sa.String(length=20),
            nullable=True,
            comment="The version the Lesson was completed in.",
        ),
    )
    op.execute(
        """
        UPDATE completed_lessons c SET syllabus_version = COALESCE(
            (SELECT a.syllabus_version FROM lesson_quiz_attempts a
              WHERE a.learner_id = c.learner_id AND a.stack_id = c.stack_id
                AND a.lesson_id = c.lesson_id AND a.passed
              ORDER BY a.submitted_at DESC LIMIT 1),
            (SELECT s.version FROM stacks st JOIN syllabuses s ON s.pk = st.current_syllabus_pk
              WHERE st.id = c.stack_id),
            ''
        )
        """
    )
    op.alter_column("completed_lessons", "syllabus_version", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("completed_lessons", "syllabus_version")
    op.drop_column("lessons", "content_hash")
