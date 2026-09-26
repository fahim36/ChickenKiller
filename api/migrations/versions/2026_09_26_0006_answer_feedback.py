"""grader feedback on written answers (#7)

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-26 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "answers",
        sa.Column("feedback", sa.Text(), nullable=True, comment="The grader's line (written)."),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("answers", "feedback")
