"""Multiple-select Questions

Revision ID: 0018_multiple_select
Revises: 0017_stack_syllabus_drafts
Create Date: 2026-10-03 10:00:00.000000

A Question can be `multiple_select` (ADR-0008): select all that apply, correct only when the
choices ticked are exactly its correct ones. `questions.answers` holds every correct choice ID.
A Learner's answer to one is stored in `answers.response` as the ticked IDs, comma-separated,
so that column needs no change. Written Questions stay, as legacy.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0018_multiple_select"
down_revision: str | Sequence[str] | None = "0017_stack_syllabus_drafts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TYPE_COMMENT = "multiple_choice, multiple_select or written (legacy)"
OLD_TYPE_COMMENT = "multiple_choice or written"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "questions",
        sa.Column(
            "answers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Every correct choice ID, for multiple select.",
        ),
    )
    op.alter_column(
        "questions",
        "type",
        existing_type=sa.String(length=20),
        existing_nullable=False,
        comment=NEW_TYPE_COMMENT,
        existing_comment=OLD_TYPE_COMMENT,
    )


def downgrade() -> None:
    """Downgrade schema. Multiple-select Questions, and the answers to them, can't be kept."""
    op.execute(
        "DELETE FROM answers WHERE (stack_id, question_id) IN "
        "(SELECT stack_id, id FROM questions WHERE type = 'multiple_select')"
    )
    op.execute("DELETE FROM questions WHERE type = 'multiple_select'")
    op.alter_column(
        "questions",
        "type",
        existing_type=sa.String(length=20),
        existing_nullable=False,
        comment=OLD_TYPE_COMMENT,
        existing_comment=NEW_TYPE_COMMENT,
    )
    op.drop_column("questions", "answers")
