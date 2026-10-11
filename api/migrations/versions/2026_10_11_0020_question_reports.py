"""Private Question Reports with one unresolved report per Learner and Question."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_question_reports"
down_revision: str | Sequence[str] | None = "0019_retirement_safe_retakes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "question_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(80), nullable=False),
        sa.Column("question_id", sa.String(80), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["learner_id"], ["learners.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["stack_id", "question_id"], ["questions.stack_id", "questions.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "category IN ('wrong_answer', 'ambiguous_wording', 'outdated_claim', 'broken_source')",
            name="category",
        ),
        sa.CheckConstraint("status IN ('open', 'accepted', 'resolved', 'closed')", name="status"),
    )
    op.create_index("ix_question_reports_learner_id", "question_reports", ["learner_id"])
    op.create_index(
        "uq_question_reports_unresolved",
        "question_reports",
        ["learner_id", "stack_id", "question_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('open', 'accepted')"),
    )


def downgrade() -> None:
    op.drop_table("question_reports")
