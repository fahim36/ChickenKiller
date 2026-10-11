"""Temporary owner-only recordings and durable replacement bounds."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0025_interview_audio"
down_revision = "0024_interview_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column("recording_counts", JSONB(), nullable=False, server_default="{}"),
    )
    op.alter_column("interview_sessions", "recording_counts", server_default=None)
    op.create_table(
        "interview_recordings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "interview_id",
            sa.Uuid(),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("prompt_id", sa.String(160), nullable=False),
        sa.Column("mime", sa.String(50), nullable=False),
        sa.Column("audio", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("transcript", sa.Text()),
        sa.UniqueConstraint("interview_id", "prompt_id"),
    )
    op.create_index(
        "ix_interview_recordings_interview_id", "interview_recordings", ["interview_id"]
    )
    op.create_index("ix_interview_recordings_expires_at", "interview_recordings", ["expires_at"])


def downgrade() -> None:
    op.drop_table("interview_recordings")
    op.drop_column("interview_sessions", "recording_counts")
