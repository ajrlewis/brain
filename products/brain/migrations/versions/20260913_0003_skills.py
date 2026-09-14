"""Create governed Skill tables.

Revision ID: 20260913_0003
Revises: 20260912_0002
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0003"
down_revision: str | None = "20260912_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("folder_id", UUID, nullable=True),
        sa.Column("slug", sa.String(63), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("current_version_id", UUID, nullable=True),
        sa.Column("access_policy_id", UUID, nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("steward_id", UUID, nullable=False),
        sa.Column("created_by_id", UUID, nullable=False),
        sa.Column("updated_by_id", UUID, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="ck_skills_slug_format"),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_skills_name_not_blank"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_skills_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "folder_id"],
            ["folders.organization_id", "folders.id"],
            name="fk_skills_organization_id_folder_id_folders",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "access_policy_id"],
            ["access_policies.organization_id", "access_policies.id"],
            name="fk_skills_access_policy_id_access_policies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "steward_id"],
            ["principals.organization_id", "principals.id"],
            name="fk_skills_steward_id_principals",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_id"],
            ["principals.organization_id", "principals.id"],
            name="fk_skills_created_by_id_principals",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "updated_by_id"],
            ["principals.organization_id", "principals.id"],
            name="fk_skills_updated_by_id_principals",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_skills"),
        sa.UniqueConstraint("organization_id", "id", name="uq_skills_organization_id_id"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_skills_organization_id_slug"),
    )
    op.create_table(
        "skill_versions",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("skill_id", UUID, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_by_id", UUID, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("version > 0", name="ck_skill_versions_version_positive"),
        sa.CheckConstraint(
            "length(btrim(content_markdown)) > 0", name="ck_skill_versions_content_not_blank"
        ),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'", name="ck_skill_versions_content_hash_sha256"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "skill_id"],
            ["skills.organization_id", "skills.id"],
            name="fk_skill_versions_organization_id_skill_id_skills",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_id"],
            ["principals.organization_id", "principals.id"],
            name="fk_skill_versions_created_by_id_principals",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_skill_versions"),
        sa.UniqueConstraint("id", "skill_id", name="uq_skill_versions_id_skill_id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_skill_versions_organization_id_id"),
        sa.UniqueConstraint("skill_id", "version", name="uq_skill_versions_skill_id_version"),
        sa.UniqueConstraint(
            "skill_id", "content_hash", name="uq_skill_versions_skill_id_content_hash"
        ),
    )
    op.create_foreign_key(
        "fk_skills_current_version",
        "skills",
        "skill_versions",
        ["current_version_id", "id"],
        ["id", "skill_id"],
        ondelete="RESTRICT",
    )
    op.execute("""
        CREATE FUNCTION reject_skill_version_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'skill versions are immutable'; END $$;
        CREATE TRIGGER skill_versions_immutable BEFORE UPDATE OR DELETE ON skill_versions
        FOR EACH ROW EXECUTE FUNCTION reject_skill_version_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION reject_skill_version_mutation() CASCADE")
    op.drop_constraint("fk_skills_current_version", "skills", type_="foreignkey")
    op.drop_table("skill_versions")
    op.drop_table("skills")
