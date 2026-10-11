"""Bounded optional guided-practice turns."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0026_interview_turns"
down_revision = "0025_interview_audio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column("turns", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.alter_column("interview_sessions", "turns", server_default=None)


def downgrade() -> None:
    op.drop_column("interview_sessions", "turns")
