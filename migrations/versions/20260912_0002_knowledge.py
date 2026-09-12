"""Create governed knowledge tables.

Revision ID: 20260912_0002
Revises: 20260912_0001
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260912_0002"
down_revision: str | None = "20260912_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def tenant_principal_fk(column: str, table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["organization_id", column],
        ["principals.organization_id", "principals.id"],
        name=f"fk_{table}_{column}_principals",
        ondelete="RESTRICT",
    )


def policy_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["organization_id", "access_policy_id"],
        ["access_policies.organization_id", "access_policies.id"],
        name=f"fk_{table}_access_policy_id_access_policies",
        ondelete="RESTRICT",
    )


def upgrade() -> None:
    op.create_table(
        "folders",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("parent_id", UUID, nullable=True),
        sa.Column("kind", sa.String(16), server_default="page", nullable=False),
        sa.Column("slug", sa.String(63), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("access_policy_id", UUID, nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("steward_id", UUID, nullable=False),
        sa.Column("created_by_id", UUID, nullable=False),
        sa.Column("updated_by_id", UUID, nullable=False),
        *timestamps(),
        sa.CheckConstraint("kind = 'page'", name="ck_folders_kind_page_only"),
        sa.CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="ck_folders_slug_format"),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_folders_name_not_blank"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_folders_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        policy_fk("folders"),
        tenant_principal_fk("steward_id", "folders"),
        tenant_principal_fk("created_by_id", "folders"),
        tenant_principal_fk("updated_by_id", "folders"),
        sa.PrimaryKeyConstraint("id", name="pk_folders"),
        sa.UniqueConstraint("organization_id", "id", name="uq_folders_organization_id_id"),
        sa.UniqueConstraint(
            "organization_id", "id", "kind", name="uq_folders_organization_id_id_kind"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "parent_id",
            "kind",
            "slug",
            name="uq_folders_sibling_slug",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_foreign_key(
        "fk_folders_parent",
        "folders",
        "folders",
        ["organization_id", "parent_id", "kind"],
        ["organization_id", "id", "kind"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "sources",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("source_type", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("canonical_uri", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(255), nullable=False),
        sa.Column("access_policy_id", UUID, nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column(
            "provenance", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("created_by_id", UUID, nullable=False),
        sa.Column("updated_by_id", UUID, nullable=False),
        sa.Column("steward_id", UUID, nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "length(btrim(source_type)) > 0", name="ck_sources_source_type_not_blank"
        ),
        sa.CheckConstraint("length(btrim(title)) > 0", name="ck_sources_title_not_blank"),
        sa.CheckConstraint("length(btrim(status)) > 0", name="ck_sources_status_not_blank"),
        sa.CheckConstraint("jsonb_typeof(metadata) = 'object'", name="ck_sources_metadata_object"),
        sa.CheckConstraint(
            "jsonb_typeof(provenance) = 'object'", name="ck_sources_provenance_object"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_sources_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        policy_fk("sources"),
        tenant_principal_fk("created_by_id", "sources"),
        tenant_principal_fk("updated_by_id", "sources"),
        tenant_principal_fk("steward_id", "sources"),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint("organization_id", "id", name="uq_sources_organization_id_id"),
    )
    op.create_index(
        "uq_sources_external_identity",
        "sources",
        ["organization_id", "source_type", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.create_table(
        "pages",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("folder_id", UUID, nullable=True),
        sa.Column("slug", sa.String(63), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("current_version_id", UUID, nullable=True),
        sa.Column("access_policy_id", UUID, nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("steward_id", UUID, nullable=False),
        sa.Column("created_by_id", UUID, nullable=False),
        sa.Column("updated_by_id", UUID, nullable=False),
        *timestamps(),
        sa.CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="ck_pages_slug_format"),
        sa.CheckConstraint("length(btrim(title)) > 0", name="ck_pages_title_not_blank"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_pages_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "folder_id"],
            ["folders.organization_id", "folders.id"],
            name="fk_pages_organization_id_folder_id_folders",
            ondelete="RESTRICT",
        ),
        policy_fk("pages"),
        tenant_principal_fk("steward_id", "pages"),
        tenant_principal_fk("created_by_id", "pages"),
        tenant_principal_fk("updated_by_id", "pages"),
        sa.PrimaryKeyConstraint("id", name="pk_pages"),
        sa.UniqueConstraint("organization_id", "id", name="uq_pages_organization_id_id"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_pages_organization_id_slug"),
    )
    op.create_table(
        "page_versions",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("page_id", UUID, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_by_id", UUID, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("version > 0", name="ck_page_versions_version_positive"),
        sa.CheckConstraint(
            "length(btrim(content_markdown)) > 0", name="ck_page_versions_content_not_blank"
        ),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'", name="ck_page_versions_content_hash_sha256"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "page_id"],
            ["pages.organization_id", "pages.id"],
            name="fk_page_versions_organization_id_page_id_pages",
            ondelete="RESTRICT",
        ),
        tenant_principal_fk("created_by_id", "page_versions"),
        sa.PrimaryKeyConstraint("id", name="pk_page_versions"),
        sa.UniqueConstraint("id", "page_id", name="uq_page_versions_id_page_id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_page_versions_organization_id_id"),
        sa.UniqueConstraint("page_id", "version", name="uq_page_versions_page_id_version"),
        sa.UniqueConstraint(
            "page_id", "content_hash", name="uq_page_versions_page_id_content_hash"
        ),
    )
    op.create_foreign_key(
        "fk_pages_current_version",
        "pages",
        "page_versions",
        ["current_version_id", "id"],
        ["id", "page_id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "page_version_sources",
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("page_version_id", UUID, nullable=False),
        sa.Column("source_id", UUID, nullable=False),
        sa.Column("relationship", sa.String(255), nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.CheckConstraint(
            "length(btrim(relationship)) > 0", name="ck_page_version_sources_relationship_not_blank"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(metadata) = 'object'", name="ck_page_version_sources_metadata_object"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "page_version_id"],
            ["page_versions.organization_id", "page_versions.id"],
            name="fk_page_version_sources_page_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_id"],
            ["sources.organization_id", "sources.id"],
            name="fk_page_version_sources_source",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "page_version_id", "source_id", "relationship", name="pk_page_version_sources"
        ),
    )
    op.execute("""
        CREATE FUNCTION reject_page_version_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'page versions are immutable'; END $$;
        CREATE TRIGGER page_versions_immutable BEFORE UPDATE OR DELETE ON page_versions
        FOR EACH ROW EXECUTE FUNCTION reject_page_version_mutation();
    """)
    op.execute("""
        CREATE FUNCTION reject_folder_cycle() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.parent_id = NEW.id OR EXISTS (
            WITH RECURSIVE ancestors(id, parent_id) AS (
              SELECT id, parent_id FROM folders
              WHERE id = NEW.parent_id AND organization_id = NEW.organization_id
              UNION ALL
              SELECT f.id, f.parent_id FROM folders f JOIN ancestors a ON f.id = a.parent_id
              WHERE f.organization_id = NEW.organization_id
            ) SELECT 1 FROM ancestors WHERE id = NEW.id
          ) THEN RAISE EXCEPTION 'folder cycle is forbidden'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER folders_no_cycles BEFORE INSERT OR UPDATE OF parent_id ON folders
        FOR EACH ROW EXECUTE FUNCTION reject_folder_cycle();
    """)
    op.execute("""
        CREATE FUNCTION reject_nonempty_folder_deletion() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL AND (
            EXISTS (SELECT 1 FROM folders WHERE parent_id = NEW.id AND deleted_at IS NULL)
            OR EXISTS (SELECT 1 FROM pages WHERE folder_id = NEW.id AND deleted_at IS NULL)
          ) THEN RAISE EXCEPTION 'non-empty folders cannot be deleted'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER folders_not_deleted_while_nonempty BEFORE UPDATE OF deleted_at ON folders
        FOR EACH ROW EXECUTE FUNCTION reject_nonempty_folder_deletion();
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS reject_nonempty_folder_deletion() CASCADE")
    op.execute("DROP FUNCTION reject_folder_cycle() CASCADE")
    op.execute("DROP FUNCTION reject_page_version_mutation() CASCADE")
    op.drop_table("page_version_sources")
    op.drop_constraint("fk_pages_current_version", "pages", type_="foreignkey")
    op.drop_table("page_versions")
    op.drop_table("pages")
    op.drop_index("uq_sources_external_identity", table_name="sources")
    op.drop_table("sources")
    op.drop_table("folders")
