"""lesson quiz attempts and answers (#6)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-26 14:38:14.442680

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OPEN = sa.text("submitted_at IS NULL")


def _learner_stack_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["learner_id", "stack_id"],
        ["learner_stacks.learner_id", "learner_stacks.stack_id"],
        name=op.f(f"fk_{table}_learner_id_learner_stacks"),
        ondelete="CASCADE",
    )


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "lesson_quiz_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column("lesson_id", sa.String(length=80), nullable=False, comment="Permanent ID."),
        sa.Column(
            "syllabus_version",
            sa.String(length=20),
            nullable=False,
            comment="The version the Questions come from, pinned at start.",
        ),
        sa.Column(
            "question_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Permanent IDs of the Questions drawn, in the order they are asked.",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correct_count", sa.Integer(), nullable=True, comment="Set on submission."),
        sa.Column("passed", sa.Boolean(), nullable=True, comment="Set on submission."),
        _learner_stack_fk("lesson_quiz_attempts"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lesson_quiz_attempts")),
    )
    op.create_index(
        "uq_lesson_quiz_attempts_one_open",
        "lesson_quiz_attempts",
        ["learner_id", "stack_id", "lesson_id"],
        unique=True,
        postgresql_where=_OPEN,
    )
    op.create_table(
        "answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column("question_id", sa.String(length=80), nullable=False, comment="Permanent ID."),
        sa.Column("syllabus_version", sa.String(length=20), nullable=False),
        sa.Column("context", sa.String(length=20), nullable=False, comment="lesson_quiz, for now"),
        sa.Column("lesson_quiz_attempt_id", sa.Uuid(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "context <> 'lesson_quiz' OR lesson_quiz_attempt_id IS NOT NULL",
            name=op.f("ck_answers_context_link"),
        ),
        _learner_stack_fk("answers"),
        sa.ForeignKeyConstraint(
            ["lesson_quiz_attempt_id"],
            ["lesson_quiz_attempts.id"],
            name=op.f("fk_answers_lesson_quiz_attempt_id_lesson_quiz_attempts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_answers")),
        sa.UniqueConstraint(
            "lesson_quiz_attempt_id",
            "question_id",
            name=op.f("uq_answers_lesson_quiz_attempt_id_question_id"),
        ),
    )
    op.create_index(
        "ix_answers_learner_question", "answers", ["learner_id", "stack_id", "question_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_answers_learner_question", table_name="answers")
    op.drop_table("answers")
    op.drop_index(
        "uq_lesson_quiz_attempts_one_open",
        table_name="lesson_quiz_attempts",
        postgresql_where=_OPEN,
    )
    op.drop_table("lesson_quiz_attempts")
