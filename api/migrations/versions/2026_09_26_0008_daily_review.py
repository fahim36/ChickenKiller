"""daily review (#9)

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-26 15:46:36.954670

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "review_days",
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column("day", sa.Date(), nullable=False, comment="In the Learner's zone."),
        sa.Column("first_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["learner_id", "stack_id"],
            ["learner_stacks.learner_id", "learner_stacks.stack_id"],
            name=op.f("fk_review_days_learner_id_learner_stacks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("learner_id", "stack_id", "day", name=op.f("pk_review_days")),
    )
    op.create_table(
        "review_rounds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column(
            "day", sa.Date(), nullable=False, comment="The review day, in the Learner's zone."
        ),
        sa.Column("number", sa.Integer(), nullable=False, comment="1 to 3 within the day."),
        sa.Column(
            "syllabus_version",
            sa.String(length=20),
            nullable=False,
            comment="The version the Questions come from, pinned at opening.",
        ),
        sa.Column(
            "question_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Permanent IDs of the Questions, in the order they are asked.",
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the last Question was answered.",
        ),
        sa.CheckConstraint("number BETWEEN 1 AND 3", name=op.f("ck_review_rounds_number_in_day")),
        sa.ForeignKeyConstraint(
            ["learner_id", "stack_id", "day"],
            ["review_days.learner_id", "review_days.stack_id", "review_days.day"],
            name=op.f("fk_review_rounds_learner_id_review_days"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_rounds")),
        sa.UniqueConstraint(
            "learner_id",
            "stack_id",
            "day",
            "number",
            name=op.f("uq_review_rounds_learner_id_stack_id_day_number"),
        ),
    )
    op.add_column("answers", sa.Column("review_round_id", sa.Uuid(), nullable=True))
    op.alter_column(
        "answers",
        "context",
        existing_type=sa.VARCHAR(length=20),
        comment="lesson_quiz, retake or review_round",
        existing_comment="lesson_quiz, for now",
        existing_nullable=False,
    )
    op.create_unique_constraint(
        op.f("uq_answers_review_round_id_question_id"),
        "answers",
        ["review_round_id", "question_id"],
    )
    op.create_foreign_key(
        op.f("fk_answers_review_round_id_review_rounds"),
        "answers",
        "review_rounds",
        ["review_round_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        op.f("ck_answers_review_round_link"),
        "answers",
        "context <> 'review_round' OR review_round_id IS NOT NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("ck_answers_review_round_link"), "answers", type_="check")
    op.drop_constraint(
        op.f("fk_answers_review_round_id_review_rounds"), "answers", type_="foreignkey"
    )
    op.drop_constraint(op.f("uq_answers_review_round_id_question_id"), "answers", type_="unique")
    op.alter_column(
        "answers",
        "context",
        existing_type=sa.VARCHAR(length=20),
        comment="lesson_quiz, for now",
        existing_comment="lesson_quiz, retake or review_round",
        existing_nullable=False,
    )
    op.drop_column("answers", "review_round_id")
    op.drop_table("review_rounds")
    op.drop_table("review_days")
