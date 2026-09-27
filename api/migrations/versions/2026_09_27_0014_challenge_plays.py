"""Playing today's Daily Challenge (#17, #7)

Revision ID: 0014_challenge_plays
Revises: 0013_daily_challenges
Create Date: 2026-09-27 12:00:00.000000

- `challenge_plays`: one row per Learner, Stack and Daily Challenge they have played, with when
  it was started and finished, the UTC Day it was finished on, whether that was the
  Challenge's own Day (the Streak, #18, counts only those), and the score.
- `answers.challenge_play_id`: a Daily Challenge's first answer to each Question, as an
  `Answer` with `context='daily_challenge'`, one per Question of the play. Its `correct` is
  null when grading failed: that Question is ungraded.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014_challenge_plays"
down_revision: str | Sequence[str] | None = "0013_daily_challenges"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "challenge_plays",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column(
            "challenge_number",
            sa.Integer(),
            nullable=False,
            comment="The Daily Challenge's number.",
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, comment="The first answer."
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "finished_day", sa.Date(), nullable=True, comment="The UTC Day it was finished on."
        ),
        sa.Column(
            "on_its_day",
            sa.Boolean(),
            nullable=True,
            comment="Finished on the Challenge's own Day: only these count toward a Streak (#18).",
        ),
        sa.Column(
            "score",
            sa.Integer(),
            nullable=True,
            comment="First answers that were correct. Set when finished.",
        ),
        sa.Column(
            "out_of",
            sa.Integer(),
            nullable=True,
            comment="Questions answered, ungraded ones included. Set when finished.",
        ),
        sa.ForeignKeyConstraint(
            ["learner_id", "stack_id"],
            ["learner_stacks.learner_id", "learner_stacks.stack_id"],
            name=op.f("fk_challenge_plays_learner_id_learner_stacks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["stack_id", "challenge_number"],
            ["daily_challenges.stack_id", "daily_challenges.number"],
            name=op.f("fk_challenge_plays_stack_id_daily_challenges"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_challenge_plays")),
        sa.UniqueConstraint(
            "learner_id",
            "stack_id",
            "challenge_number",
            name=op.f("uq_challenge_plays_learner_id_stack_id_challenge_number"),
        ),
    )
    op.add_column("answers", sa.Column("challenge_play_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_answers_challenge_play_id_challenge_plays"),
        "answers",
        "challenge_plays",
        ["challenge_play_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        op.f("uq_answers_challenge_play_id_question_id"),
        "answers",
        ["challenge_play_id", "question_id"],
    )
    op.create_check_constraint(
        op.f("ck_answers_challenge_play_link"),
        "answers",
        "context <> 'daily_challenge' OR challenge_play_id IS NOT NULL",
    )
    op.alter_column(
        "answers",
        "context",
        existing_type=sa.VARCHAR(length=20),
        comment="lesson_quiz, retake, review or daily_challenge",
        existing_comment="lesson_quiz, retake or review",
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema. Daily Challenge answers go with their plays."""
    op.execute("DELETE FROM answers WHERE context = 'daily_challenge'")
    op.alter_column(
        "answers",
        "context",
        existing_type=sa.VARCHAR(length=20),
        comment="lesson_quiz, retake or review",
        existing_comment="lesson_quiz, retake, review or daily_challenge",
        existing_nullable=False,
    )
    op.drop_constraint(op.f("ck_answers_challenge_play_link"), "answers", type_="check")
    op.drop_constraint(op.f("uq_answers_challenge_play_id_question_id"), "answers", type_="unique")
    op.drop_constraint(
        op.f("fk_answers_challenge_play_id_challenge_plays"), "answers", type_="foreignkey"
    )
    op.drop_column("answers", "challenge_play_id")
    op.drop_table("challenge_plays")
