"""Stack and Syllabus drafts

Revision ID: 0017_stack_syllabus_drafts
Revises: 0016_keys_tokens_drafts
Create Date: 2026-09-29 10:00:00.000000

A new Stack is built through drafts (app/stack_builder.py): a `stack` draft is the request
from the Add a Stack button or the MCP connector, and a `syllabus` draft is its weekly plan,
before the `questions` drafts of its quiz setup.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0017_stack_syllabus_drafts"
down_revision: str | Sequence[str] | None = "0016_keys_tokens_drafts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("draft_kind", "content_drafts", type_="check")
    op.create_check_constraint(
        "draft_kind",
        "content_drafts",
        "kind IN ('questions', 'challenge', 'stack', 'syllabus')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM content_drafts WHERE kind IN ('stack', 'syllabus')")
    op.drop_constraint("draft_kind", "content_drafts", type_="check")
    op.create_check_constraint("draft_kind", "content_drafts", "kind IN ('questions', 'challenge')")
