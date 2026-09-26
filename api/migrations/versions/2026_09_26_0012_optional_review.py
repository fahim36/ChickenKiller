"""optional Review, no rounds (#9, ADR-0003)

Revision ID: 0012_optional_review
Revises: 0011_stack_question_bank
Create Date: 2026-09-26 23:00:00.000000

Review is an optional queue drawn fresh on each request, so nothing about it is stored but its
answers.

- `review_days` and `review_rounds` are dropped, and with them the Daily Review's rounds and the
  old Streak (#11), which was computed from them.
- `answers.review_round_id` is dropped. Answers given in Review Rounds are kept, as
  `context='review'`: they still count for Missed Questions and for leaving the queue.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0012_optional_review"
down_revision: str | Sequence[str] | None = "0011_stack_question_bank"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f("ck_answers_review_round_link"), "answers", type_="check")
    op.drop_constraint(
        op.f("fk_answers_review_round_id_review_rounds"), "answers", type_="foreignkey"
    )
    op.drop_constraint(op.f("uq_answers_review_round_id_question_id"), "answers", type_="unique")
    op.drop_column("answers", "review_round_id")
    op.execute("UPDATE answers SET context = 'review' WHERE context = 'review_round'")
    op.alter_column(
        "answers",
        "context",
        existing_type=sa.VARCHAR(length=20),
        comment="lesson_quiz, retake or review",
        existing_comment="lesson_quiz, retake or review_round",
        existing_nullable=False,
    )
    op.drop_table("review_rounds")
    op.drop_table("review_days")


def downgrade() -> None:
    """Downgrade schema. The rounds are gone: Review answers stay `context='review'`, linked to
    no round, which the restored check constraint allows."""
    op.create_table(
        "review_days",
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column("day", sa.Date(), nullable=False, comment="A UTC Day."),
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
        sa.Column("day", sa.Date(), nullable=False, comment="The review Day, in UTC."),
        sa.Column("number", sa.Integer(), nullable=False, comment="1 to 3 within the day."),
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
    op.alter_column(
        "answers",
        "context",
        existing_type=sa.VARCHAR(length=20),
        comment="lesson_quiz, retake or review_round",
        existing_comment="lesson_quiz, retake or review",
        existing_nullable=False,
    )
    op.add_column("answers", sa.Column("review_round_id", sa.Uuid(), nullable=True))
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
