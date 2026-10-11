"""Consent settings and atomic interview request ledger."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0024_interview_feedback"
down_revision = "0023_interview_self_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interview_settings",
        sa.Column(
            "learner_id",
            sa.Integer(),
            sa.ForeignKey("learners.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("processing_consent", sa.Boolean(), nullable=False),
        sa.Column("free_project_confirmed", sa.Boolean(), nullable=False),
        sa.Column("key_fingerprint", sa.String(64)),
    )
    op.create_table(
        "interview_operations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "interview_id",
            sa.Uuid(),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "learner_id",
            sa.Integer(),
            sa.ForeignKey("learners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("prompt_id", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_text", sa.Text()),
        sa.Column("result", JSONB()),
    )
    op.create_index(
        "ix_interview_operations_interview_id", "interview_operations", ["interview_id"]
    )
    op.create_index(
        "uq_interview_operation_inflight",
        "interview_operations",
        ["learner_id"],
        unique=True,
        postgresql_where=sa.text("state = 'running'"),
    )


def downgrade() -> None:
    op.drop_table("interview_operations")
    op.drop_table("interview_settings")
