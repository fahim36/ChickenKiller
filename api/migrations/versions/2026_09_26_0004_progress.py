"""progress: completed lessons and milestone ticks (#5)

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-26 09:40:19.993756

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _learner_stack_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["learner_id", "stack_id"],
        ["learner_stacks.learner_id", "learner_stacks.stack_id"],
        name=op.f(f"fk_{table}_learner_id_learner_stacks"),
        ondelete="CASCADE",
    )


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "completed_lessons",
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column("lesson_id", sa.String(length=80), nullable=False, comment="Permanent ID."),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        _learner_stack_fk("completed_lessons"),
        sa.PrimaryKeyConstraint(
            "learner_id", "stack_id", "lesson_id", name=op.f("pk_completed_lessons")
        ),
    )
    op.create_table(
        "milestone_ticks",
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column("milestone_id", sa.String(length=80), nullable=False, comment="Permanent ID."),
        sa.Column("ticked_at", sa.DateTime(timezone=True), nullable=False),
        _learner_stack_fk("milestone_ticks"),
        sa.PrimaryKeyConstraint(
            "learner_id", "stack_id", "milestone_id", name=op.f("pk_milestone_ticks")
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("milestone_ticks")
    op.drop_table("completed_lessons")
