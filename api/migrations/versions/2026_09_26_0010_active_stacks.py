"""many Active Stacks and UTC Days (#4, ADR-0003, ADR-0005)

Revision ID: 0010_active_stacks
Revises: 0009_updated_lessons
Create Date: 2026-09-26 22:00:00.000000

- `learner_stacks.active`: a Learner has any number of Active Stacks. Each Learner's former
  single Active Stack (`learners.active_stack_id`) stays active; their other Stacks become
  inactive, with their progress kept.
- `learners.time_zone` is dropped: every Day is a UTC Day. Review Days and Rounds already
  stored keep their dates, which are read as UTC Days from now on.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_active_stacks"
down_revision: str | Sequence[str] | None = "0009_updated_lessons"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "learner_stacks",
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="Whether it is one of the Learner's Active Stacks.",
        ),
    )
    op.execute(
        """
        UPDATE learner_stacks ls SET active = EXISTS (
            SELECT 1 FROM learners l WHERE l.id = ls.learner_id AND l.active_stack_id = ls.stack_id
        )
        """
    )
    op.drop_constraint("fk_learners_active_stack_id_stacks", "learners", type_="foreignkey")
    op.drop_column("learners", "active_stack_id")
    op.drop_column("learners", "time_zone")
    op.alter_column(
        "review_days",
        "day",
        existing_type=sa.Date(),
        existing_nullable=False,
        comment="A UTC Day.",
        existing_comment="In the Learner's zone.",
    )
    op.alter_column(
        "review_rounds",
        "day",
        existing_type=sa.Date(),
        existing_nullable=False,
        comment="The review Day, in UTC.",
        existing_comment="The review day, in the Learner's zone.",
    )


def downgrade() -> None:
    """Downgrade schema. Each Learner keeps one of their Active Stacks, the first they
    started, and gets the time zone UTC."""
    op.alter_column(
        "review_rounds",
        "day",
        existing_type=sa.Date(),
        existing_nullable=False,
        comment="The review day, in the Learner's zone.",
        existing_comment="The review Day, in UTC.",
    )
    op.alter_column(
        "review_days",
        "day",
        existing_type=sa.Date(),
        existing_nullable=False,
        comment="In the Learner's zone.",
        existing_comment="A UTC Day.",
    )
    op.add_column(
        "learners",
        sa.Column("time_zone", sa.String(length=64), nullable=True, comment="An IANA name."),
    )
    op.add_column("learners", sa.Column("active_stack_id", sa.String(length=80), nullable=True))
    op.create_foreign_key(
        "fk_learners_active_stack_id_stacks",
        "learners",
        "stacks",
        ["active_stack_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE learners l SET
            active_stack_id = (
                SELECT ls.stack_id FROM learner_stacks ls
                 WHERE ls.learner_id = l.id AND ls.active
                 ORDER BY ls.started_at, ls.stack_id LIMIT 1
            ),
            time_zone = 'UTC'
        """
    )
    op.execute("UPDATE learners SET time_zone = NULL WHERE active_stack_id IS NULL")
    op.drop_column("learner_stacks", "active")
