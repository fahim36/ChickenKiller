"""Persist retirement waivers separately from answers."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_retirement_safe_retakes"
down_revision: str | Sequence[str] | None = "0018_multiple_select"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("retakes", sa.Column("waived_reason", sa.Text(), nullable=True))
    op.add_column("retakes", sa.Column("replacement_notice", sa.Text(), nullable=True))
    op.alter_column(
        "retakes",
        "done_at",
        existing_type=sa.DateTime(timezone=True),
        comment="When a Retake was answered correctly or waived.",
        existing_comment="When a Retake was answered correctly.",
    )


def downgrade() -> None:
    op.alter_column(
        "retakes",
        "done_at",
        existing_type=sa.DateTime(timezone=True),
        comment="When a Retake was answered correctly.",
        existing_comment="When a Retake was answered correctly or waived.",
    )
    op.drop_column("retakes", "replacement_notice")
    op.drop_column("retakes", "waived_reason")
