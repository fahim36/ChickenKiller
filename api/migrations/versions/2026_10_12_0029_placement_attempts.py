"""Private saved placement and learner-scoped Question reservations."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0029_placement_attempts"
down_revision = "0028_question_exposure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "placement_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "learner_id",
            sa.Integer(),
            sa.ForeignKey("learners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stack_id", sa.String(80), sa.ForeignKey("stacks.id"), nullable=False),
        sa.Column("week_id", sa.String(80), nullable=False),
        sa.Column("syllabus_version", sa.String(20), nullable=False),
        sa.Column("teaching_revision", sa.String(64), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("questions", postgresql.JSONB(), nullable=False),
        sa.Column("responses", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB()),
        sa.CheckConstraint(
            "state IN ('open', 'submitted', 'cancelled', 'abandoned')",
            name="ck_placement_attempts_state",
        ),
    )
    op.create_index(
        "uq_placement_open",
        "placement_attempts",
        ["learner_id", "stack_id"],
        unique=True,
        postgresql_where=sa.text("state = 'open'"),
    )
    op.create_index(
        "uq_placement_submitted_revision",
        "placement_attempts",
        ["learner_id", "stack_id", "week_id", "teaching_revision"],
        unique=True,
        postgresql_where=sa.text("state = 'submitted'"),
    )
    op.create_table(
        "placement_reservations",
        sa.Column(
            "learner_id",
            sa.Integer(),
            sa.ForeignKey("learners.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("stack_id", sa.String(80), sa.ForeignKey("stacks.id"), primary_key=True),
        sa.Column("question_id", sa.String(80), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.Uuid(),
            sa.ForeignKey("placement_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_placement_reservations_attempt_id", "placement_reservations", ["attempt_id"]
    )


def downgrade() -> None:
    op.drop_table("placement_reservations")
    op.drop_table("placement_attempts")
