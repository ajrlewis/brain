"""Create Cortex conversations and public messages."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260915_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", UUID, nullable=False),
        sa.Column("owner_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(200)),
        sa.Column("version", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "version >= 0 AND version % 2 = 0", name="ck_conversations_even_version"
        ),
        sa.CheckConstraint(
            "char_length(owner_id) BETWEEN 1 AND 255", name="ck_conversations_owner_id_length"
        ),
        sa.CheckConstraint(
            "title IS NULL OR char_length(title) BETWEEN 1 AND 200",
            name="ck_conversations_title_length",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
    )
    op.create_index(
        "ix_conversations_owner_updated", "conversations", ["owner_id", "updated_at", "id"]
    )
    op.create_table(
        "conversation_messages",
        sa.Column("id", UUID, nullable=False),
        sa.Column("conversation_id", UUID, nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "char_length(content) BETWEEN 1 AND 8000",
            name="ck_conversation_messages_content_length",
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_conversation_messages_positive_sequence"),
        sa.CheckConstraint(
            "role IN ('system', 'user', 'assistant')", name="ck_conversation_messages_valid_role"
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_conversation_messages_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_conversation_messages"),
        sa.UniqueConstraint(
            "conversation_id", "sequence", name="uq_conversation_messages_message_sequence"
        ),
    )


def downgrade() -> None:
    op.drop_table("conversation_messages")
    op.drop_index("ix_conversations_owner_updated", table_name="conversations")
    op.drop_table("conversations")
