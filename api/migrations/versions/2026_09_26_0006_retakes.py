"""retakes (#8)

Revision ID: 0006_retakes
Revises: 0005
Create Date: 2026-09-26 15:01:10.768185

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_retakes"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "retakes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column("lesson_quiz_attempt_id", sa.Uuid(), nullable=False),
        sa.Column(
            "missed_question_id", sa.String(length=80), nullable=False, comment="Permanent ID."
        ),
        sa.Column(
            "asked_question_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Permanent IDs of the siblings asked, in order; the last is waiting.",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "done_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When a Retake was answered correctly.",
        ),
        sa.ForeignKeyConstraint(
            ["learner_id", "stack_id"],
            ["learner_stacks.learner_id", "learner_stacks.stack_id"],
            name=op.f("fk_retakes_learner_id_learner_stacks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lesson_quiz_attempt_id"],
            ["lesson_quiz_attempts.id"],
            name=op.f("fk_retakes_lesson_quiz_attempt_id_lesson_quiz_attempts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retakes")),
        sa.UniqueConstraint(
            "lesson_quiz_attempt_id",
            "missed_question_id",
            name=op.f("uq_retakes_lesson_quiz_attempt_id_missed_question_id"),
        ),
    )
    op.create_index(
        op.f("ix_retakes_lesson_quiz_attempt_id"), "retakes", ["lesson_quiz_attempt_id"]
    )
    op.add_column("answers", sa.Column("retake_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_answers_retake_id"), "answers", ["retake_id"])
    op.create_foreign_key(
        op.f("fk_answers_retake_id_retakes"),
        "answers",
        "retakes",
        ["retake_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        op.f("ck_answers_retake_link"), "answers", "context <> 'retake' OR retake_id IS NOT NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("ck_answers_retake_link"), "answers", type_="check")
    op.drop_constraint(op.f("fk_answers_retake_id_retakes"), "answers", type_="foreignkey")
    op.drop_index(op.f("ix_answers_retake_id"), table_name="answers")
    op.drop_column("answers", "retake_id")
    op.drop_index(op.f("ix_retakes_lesson_quiz_attempt_id"), table_name="retakes")
    op.drop_table("retakes")
