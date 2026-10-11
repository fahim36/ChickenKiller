"""Associate accepted reports with imported corrections."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_report_corrections"
down_revision: str | Sequence[str] | None = "0020_question_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("question_reports", sa.Column("correction_kind", sa.String(20), nullable=True))
    op.add_column("question_reports", sa.Column("replacement_id", sa.String(80), nullable=True))
    op.add_column(
        "question_reports", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("question_reports", sa.Column("resolution_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    for name in ("resolution_reason", "resolved_at", "replacement_id", "correction_kind"):
        op.drop_column("question_reports", name)
