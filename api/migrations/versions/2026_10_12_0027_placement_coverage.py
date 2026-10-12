"""Reviewed placement coverage per Syllabus."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0027_placement_coverage"
down_revision = "0026_interview_turns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "placement_coverage",
        sa.Column(
            "syllabus_pk",
            sa.Integer(),
            sa.ForeignKey("syllabuses.pk", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("week_id", sa.String(80), primary_key=True),
        sa.Column("document", postgresql.JSONB(), nullable=False),
        sa.Column("teaching_revision", sa.String(64), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("placement_coverage")
