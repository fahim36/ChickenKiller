"""Record targeted Review uptake and completed graded practice."""

import sqlalchemy as sa
from alembic import op

revision = "0022_targeted_practice"
down_revision = "0021_report_corrections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "targeted_review_visits",
        sa.Column("learner_id", sa.Integer(), primary_key=True),
        sa.Column("stack_id", sa.String(80), primary_key=True),
        sa.Column("concept_id", sa.String(80), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.ForeignKeyConstraint(
            ["learner_id", "stack_id"],
            ["learner_stacks.learner_id", "learner_stacks.stack_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_table(
        "targeted_practices",
        sa.Column(
            "answer_id",
            sa.Integer(),
            sa.ForeignKey("answers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("concept_id", sa.String(80), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("targeted_practices")
    op.drop_table("targeted_review_visits")
