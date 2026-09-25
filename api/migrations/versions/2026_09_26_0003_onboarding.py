"""onboarding: learner_stacks and published Stacks (#4)

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-26 03:28:43.282270

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "learner_stacks",
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["learner_id"],
            ["learners.id"],
            name=op.f("fk_learner_stacks_learner_id_learners"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["stack_id"],
            ["stacks.id"],
            name=op.f("fk_learner_stacks_stack_id_stacks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("learner_id", "stack_id", name=op.f("pk_learner_stacks")),
    )
    op.add_column(
        "stacks",
        sa.Column(
            "published",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="Set by the current Syllabus. Only published Stacks can be chosen.",
        ),
    )
    # Every Active Stack has its Learner's record.
    op.execute(
        "INSERT INTO learner_stacks (learner_id, stack_id) "
        "SELECT id, active_stack_id FROM learners WHERE active_stack_id IS NOT NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("stacks", "published")
    op.drop_table("learner_stacks")
