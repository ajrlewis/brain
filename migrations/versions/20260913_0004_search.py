"""Add derived PageVersion chunks and retrieval indexes.

Revision ID: 20260913_0004
Revises: 20260913_0003
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0004"
down_revision: str | None = "20260913_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "chunks",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("page_version_id", UUID, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("heading_path", postgresql.JSONB(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding", Vector(8), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("position >= 0", name="ck_chunks_position_nonnegative"),
        sa.CheckConstraint("length(btrim(content)) > 0", name="ck_chunks_content_not_blank"),
        sa.CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_chunks_content_hash_sha256"),
        sa.CheckConstraint(
            "jsonb_typeof(heading_path) = 'array'", name="ck_chunks_heading_path_array"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "page_version_id"],
            ["page_versions.organization_id", "page_versions.id"],
            name="fk_chunks_organization_id_page_version_id_page_versions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
        sa.UniqueConstraint(
            "page_version_id", "position", name="uq_chunks_page_version_id_position"
        ),
    )
    op.execute("CREATE INDEX ix_chunks_fts ON chunks USING gin (to_tsvector('english', content))")
    op.execute(
        "CREATE INDEX ix_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("chunks")
