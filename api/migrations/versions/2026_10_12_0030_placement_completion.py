"""Identify Lessons completed by private Placement Quiz evidence."""

import sqlalchemy as sa
from alembic import op

revision = "0030_placement_completion"
down_revision = "0029_placement_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("completed_lessons", sa.Column("placement_attempt_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_completed_lessons_placement",
        "completed_lessons",
        "placement_attempts",
        ["placement_attempt_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_completed_lessons_placement", "completed_lessons", type_="foreignkey")
    op.drop_column("completed_lessons", "placement_attempt_id")
