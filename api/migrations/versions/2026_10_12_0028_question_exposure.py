"""Question delivery history, including unanswered prompts."""

import sqlalchemy as sa
from alembic import op

revision = "0028_question_exposure"
down_revision = "0027_placement_coverage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_exposures",
        sa.Column(
            "learner_id",
            sa.Integer(),
            sa.ForeignKey("learners.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("stack_id", sa.String(80), sa.ForeignKey("stacks.id"), primary_key=True),
        sa.Column("question_id", sa.String(80), primary_key=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute("""INSERT INTO question_exposures (learner_id, stack_id, question_id, first_seen_at)
        SELECT learner_id, stack_id, question_id, MIN(answered_at) FROM answers
        GROUP BY learner_id, stack_id, question_id ON CONFLICT DO NOTHING""")


def downgrade() -> None:
    op.drop_table("question_exposures")
