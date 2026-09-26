"""Upcoming and released Daily Challenges (#16)

Revision ID: 0013_daily_challenges
Revises: 0012_optional_review
Create Date: 2026-09-27 00:00:00.000000

`daily_challenges`: one row per Daily Challenge of a Stack, with its number, UTC Day and three
Question IDs. The next `content-import` fills it from `content/<stack-id>/challenges/`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0013_daily_challenges"
down_revision: str | Sequence[str] | None = "0012_optional_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "daily_challenges",
        sa.Column("pk", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column(
            "number", sa.Integer(), nullable=False, comment="Numbered from the Stack's launch."
        ),
        sa.Column("day", sa.Date(), nullable=False, comment="Its UTC Day."),
        sa.Column(
            "question_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Permanent IDs of its three Questions, in order.",
        ),
        sa.Column(
            "content_hash",
            sa.String(length=64),
            nullable=False,
            comment="The import refuses a change once its Day has begun.",
        ),
        sa.ForeignKeyConstraint(
            ["stack_id"],
            ["stacks.id"],
            name=op.f("fk_daily_challenges_stack_id_stacks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("pk", name=op.f("pk_daily_challenges")),
        sa.UniqueConstraint("stack_id", "day", name=op.f("uq_daily_challenges_stack_id_day")),
        sa.UniqueConstraint("stack_id", "number", name=op.f("uq_daily_challenges_stack_id_number")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("daily_challenges")
