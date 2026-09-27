"""Grading keys, MCP access tokens and content drafts

Revision ID: 0016_keys_tokens_drafts
Revises: 0015_lesson_fingerprints
Create Date: 2026-09-28 10:00:00.000000

- `grading_keys`: a Learner's own LLM provider key for grading, encrypted (app/llm_keys.py).
- `access_tokens`: personal access tokens for the MCP connector, stored as SHA-256 hashes.
- `content_drafts`: Questions and Daily Challenges proposed through the connector, each with
  its author, waiting for the Admin.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0016_keys_tokens_drafts"
down_revision: str | Sequence[str] | None = "0015_lesson_fingerprints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "grading_keys",
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False, comment="nvidia"),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column(
            "key_ciphertext",
            sa.Text(),
            nullable=False,
            comment="Fernet token (LLM_KEY_SECRET).",
        ),
        sa.Column(
            "key_hint",
            sa.String(length=8),
            nullable=False,
            comment="The key's last four characters.",
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["learner_id"], ["learners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("learner_id"),
    )
    op.create_table(
        "access_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, comment="SHA-256, hex."),
        sa.Column(
            "prefix",
            sa.String(length=12),
            nullable=False,
            comment="The token's start, to recognise it.",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["learner_id"], ["learners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_access_tokens_learner_id", "access_tokens", ["learner_id"])
    op.create_table(
        "content_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("learner_id", sa.Integer(), nullable=False, comment="The author."),
        sa.Column("stack_id", sa.String(length=80), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('questions', 'challenge')", name="draft_kind"),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'exported')", name="draft_status"
        ),
        sa.ForeignKeyConstraint(["learner_id"], ["learners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_drafts_learner_id", "content_drafts", ["learner_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_content_drafts_learner_id", table_name="content_drafts")
    op.drop_table("content_drafts")
    op.drop_index("ix_access_tokens_learner_id", table_name="access_tokens")
    op.drop_table("access_tokens")
    op.drop_table("grading_keys")
