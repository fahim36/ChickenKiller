"""Private expiring interview evidence and reviewed content."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0023_interview_self_review"
down_revision = "0022_targeted_practice"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interview_content",
        sa.Column("stack_id", sa.String(80), sa.ForeignKey("stacks.id"), primary_key=True),
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("document", JSONB(), nullable=False),
    )
    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "learner_id",
            sa.Integer(),
            sa.ForeignKey("learners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stack_id", sa.String(80), sa.ForeignKey("stacks.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prompts", JSONB(), nullable=False),
        sa.Column("responses", JSONB(), nullable=False),
    )
    op.create_index("ix_interview_sessions_learner_id", "interview_sessions", ["learner_id"])
    op.create_index("ix_interview_sessions_expires_at", "interview_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_table("interview_sessions")
    op.drop_table("interview_content")
