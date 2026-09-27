"""the Stack's Question Bank, with Sources and Retired Questions (#15)

Revision ID: 0011_stack_question_bank
Revises: 0010_active_stacks
Create Date: 2026-09-26 22:00:00.000000

The Question Bank stops being part of each Syllabus version (ADR-0004):

- `concepts`, `questions` and `question_materials` are rebuilt keyed by `(stack_id, id)`, with
  each Question's Lesson tag, retirement and content hash, and `question_sources` is added. The
  old per-version rows are dropped, not converted: nothing is released yet, and the next
  `content-import` loads the bank again. Learner data names Questions by permanent ID, so it is
  untouched.
- `lessons.question_ids`: the Questions tagged to each Lesson of a version when it was imported,
  which its fingerprint includes (#13). Lessons imported before are left with none.
- `answers.syllabus_version` and `review_rounds.syllabus_version` go: a Question never changes,
  so there is nothing to pin. `lesson_quiz_attempts.syllabus_version` stays, as the version a
  pass completes the Lesson in.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0011_stack_question_bank"
down_revision: str | Sequence[str] | None = "0010_active_stacks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("question_materials")
    op.drop_index(op.f("ix_questions_syllabus_pk"), table_name="questions")
    op.drop_table("questions")
    op.drop_index(op.f("ix_concepts_syllabus_pk"), table_name="concepts")
    op.drop_table("concepts")

    op.create_table(
        "concepts",
        sa.Column("pk", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["stack_id"],
            ["stacks.id"],
            name=op.f("fk_concepts_stack_id_stacks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("pk", name=op.f("pk_concepts")),
        sa.UniqueConstraint("stack_id", "id", name=op.f("uq_concepts_stack_id_id")),
    )
    op.create_table(
        "questions",
        sa.Column("pk", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column(
            "lesson_id",
            sa.String(length=80),
            nullable=True,
            comment="Permanent ID of the Lesson it is tagged to, if any. May change (re-tag).",
        ),
        sa.Column("concept_pk", sa.Integer(), nullable=False),
        sa.Column(
            "position", sa.Integer(), nullable=False, comment="Order within the Question Bank."
        ),
        sa.Column(
            "type", sa.String(length=20), nullable=False, comment="multiple_choice or written"
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("choices", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("answer", sa.String(length=1), nullable=True),
        sa.Column("model_answer", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "material_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Permanent IDs of its Materials, in order.",
        ),
        sa.Column(
            "content_hash",
            sa.String(length=64),
            nullable=False,
            comment="Everything that never changes: the import refuses an edit.",
        ),
        sa.Column("retired_reason", sa.Text(), nullable=True, comment="Set once it is retired."),
        sa.Column(
            "replaced_by",
            sa.String(length=80),
            nullable=True,
            comment="Permanent ID of its replacement.",
        ),
        sa.Column("retired_on", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["concept_pk"],
            ["concepts.pk"],
            name=op.f("fk_questions_concept_pk_concepts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["stack_id"],
            ["stacks.id"],
            name=op.f("fk_questions_stack_id_stacks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("pk", name=op.f("pk_questions")),
        sa.UniqueConstraint("stack_id", "id", name=op.f("uq_questions_stack_id_id")),
    )
    op.create_table(
        "question_materials",
        sa.Column("question_pk", sa.Integer(), nullable=False),
        sa.Column("material_pk", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["material_pk"],
            ["materials.pk"],
            name=op.f("fk_question_materials_material_pk_materials"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_pk"],
            ["questions.pk"],
            name=op.f("fk_question_materials_question_pk_questions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("question_pk", "material_pk", name=op.f("pk_question_materials")),
    )
    op.create_table(
        "question_sources",
        sa.Column("question_pk", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("publisher", sa.Text(), nullable=False),
        sa.Column("accessed", sa.Date(), nullable=False, comment="UTC."),
        sa.Column("claim", sa.Text(), nullable=False, comment="The claim the Question relies on."),
        sa.ForeignKeyConstraint(
            ["question_pk"],
            ["questions.pk"],
            name=op.f("fk_question_sources_question_pk_questions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("question_pk", "position", name=op.f("pk_question_sources")),
    )

    op.add_column(
        "lessons",
        sa.Column(
            "question_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="The Questions tagged to it, not retired, when this version was imported.",
        ),
    )
    op.alter_column(
        "lessons",
        "content_hash",
        existing_type=sa.String(length=64),
        existing_nullable=True,
        comment=(
            "The Lesson's content as content-diff compares it (fields, Week), plus question_ids. "
            "Equal across versions means unchanged."
        ),
        existing_comment=(
            "The Lesson's content as content-diff compares it (fields, Week, Question "
            "Bank). Equal across versions means unchanged."
        ),
    )
    op.alter_column(
        "lesson_quiz_attempts",
        "syllabus_version",
        existing_type=sa.String(length=20),
        existing_nullable=False,
        comment="The Syllabus version current at start; a pass completes it there.",
        existing_comment="The version the Questions come from, pinned at start.",
    )
    op.drop_column("answers", "syllabus_version")
    op.drop_column("review_rounds", "syllabus_version")


def downgrade() -> None:
    """Downgrade schema. Question rows are dropped; re-import the old layout to fill them."""
    op.add_column(
        "review_rounds",
        sa.Column(
            "syllabus_version",
            sa.String(length=20),
            server_default="",
            nullable=False,
            comment="The version the Questions come from, pinned at opening.",
        ),
    )
    op.alter_column("review_rounds", "syllabus_version", server_default=None)
    op.add_column(
        "answers",
        sa.Column("syllabus_version", sa.String(length=20), server_default="", nullable=False),
    )
    op.alter_column("answers", "syllabus_version", server_default=None)
    op.alter_column(
        "lesson_quiz_attempts",
        "syllabus_version",
        existing_type=sa.String(length=20),
        existing_nullable=False,
        comment="The version the Questions come from, pinned at start.",
        existing_comment="The Syllabus version current at start; a pass completes it there.",
    )
    op.alter_column(
        "lessons",
        "content_hash",
        existing_type=sa.String(length=64),
        existing_nullable=True,
        comment=(
            "The Lesson's content as content-diff compares it (fields, Week, Question "
            "Bank). Equal across versions means unchanged."
        ),
        existing_comment=(
            "The Lesson's content as content-diff compares it (fields, Week), plus question_ids. "
            "Equal across versions means unchanged."
        ),
    )
    op.drop_column("lessons", "question_ids")

    op.drop_table("question_sources")
    op.drop_table("question_materials")
    op.drop_table("questions")
    op.drop_table("concepts")

    op.create_table(
        "concepts",
        sa.Column("pk", sa.Integer(), nullable=False),
        sa.Column("syllabus_pk", sa.Integer(), nullable=False),
        sa.Column("lesson_pk", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["lesson_pk"],
            ["lessons.pk"],
            name=op.f("fk_concepts_lesson_pk_lessons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["syllabus_pk"],
            ["syllabuses.pk"],
            name=op.f("fk_concepts_syllabus_pk_syllabuses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("pk", name=op.f("pk_concepts")),
        sa.UniqueConstraint("syllabus_pk", "id", name=op.f("uq_concepts_syllabus_pk_id")),
    )
    op.create_index(op.f("ix_concepts_syllabus_pk"), "concepts", ["syllabus_pk"], unique=False)
    op.create_table(
        "questions",
        sa.Column("pk", sa.Integer(), nullable=False),
        sa.Column("syllabus_pk", sa.Integer(), nullable=False),
        sa.Column("lesson_pk", sa.Integer(), nullable=False),
        sa.Column("concept_pk", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column(
            "position", sa.Integer(), nullable=False, comment="Order within its Question Bank."
        ),
        sa.Column(
            "type", sa.String(length=20), nullable=False, comment="multiple_choice or written"
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("choices", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("answer", sa.String(length=1), nullable=True),
        sa.Column("model_answer", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["concept_pk"],
            ["concepts.pk"],
            name=op.f("fk_questions_concept_pk_concepts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lesson_pk"],
            ["lessons.pk"],
            name=op.f("fk_questions_lesson_pk_lessons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["syllabus_pk"],
            ["syllabuses.pk"],
            name=op.f("fk_questions_syllabus_pk_syllabuses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("pk", name=op.f("pk_questions")),
        sa.UniqueConstraint("syllabus_pk", "id", name=op.f("uq_questions_syllabus_pk_id")),
    )
    op.create_index(op.f("ix_questions_syllabus_pk"), "questions", ["syllabus_pk"], unique=False)
    op.create_table(
        "question_materials",
        sa.Column("question_pk", sa.Integer(), nullable=False),
        sa.Column("material_pk", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["material_pk"],
            ["materials.pk"],
            name=op.f("fk_question_materials_material_pk_materials"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_pk"],
            ["questions.pk"],
            name=op.f("fk_question_materials_question_pk_questions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("question_pk", "material_pk", name=op.f("pk_question_materials")),
    )
