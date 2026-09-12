"""Create the identity and access-control foundation.

Revision ID: 20260912_0001
Revises:
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260912_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def timestamp_columns() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(length=63), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="ck_organizations_slug_format"
        ),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_organizations_name_not_blank"),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_table(
        "principals",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("external_subject", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "kind IN ('user', 'service', 'agent')", name="ck_principals_kind_allowed"
        ),
        sa.CheckConstraint(
            "length(btrim(display_name)) > 0", name="ck_principals_display_name_not_blank"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_principals_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_principals"),
        sa.UniqueConstraint(
            "organization_id",
            "external_subject",
            name="uq_principals_organization_id_external_subject",
        ),
        sa.UniqueConstraint("organization_id", "id", name="uq_principals_organization_id_id"),
    )
    op.create_table(
        "groups",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("slug", sa.String(length=63), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="ck_groups_slug_format"),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_groups_name_not_blank"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_groups_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_groups"),
        sa.UniqueConstraint("organization_id", "id", name="uq_groups_organization_id_id"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_groups_organization_id_slug"),
    )
    op.create_table(
        "access_policies",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_access_policies_name_not_blank"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_access_policies_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_access_policies"),
        sa.UniqueConstraint("organization_id", "id", name="uq_access_policies_organization_id_id"),
        sa.UniqueConstraint(
            "organization_id", "name", name="uq_access_policies_organization_id_name"
        ),
    )
    op.create_table(
        "group_memberships",
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("group_id", UUID, nullable=False),
        sa.Column("principal_id", UUID, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "group_id"],
            ["groups.organization_id", "groups.id"],
            name="fk_group_memberships_group",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "principal_id"],
            ["principals.organization_id", "principals.id"],
            name="fk_group_memberships_principal",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "organization_id", "group_id", "principal_id", name="pk_group_memberships"
        ),
    )
    op.create_table(
        "access_policy_groups",
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("access_policy_id", UUID, nullable=False),
        sa.Column("group_id", UUID, nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id", "access_policy_id"],
            ["access_policies.organization_id", "access_policies.id"],
            name="fk_access_policy_groups_policy",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "group_id"],
            ["groups.organization_id", "groups.id"],
            name="fk_access_policy_groups_group",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "organization_id", "access_policy_id", "group_id", name="pk_access_policy_groups"
        ),
    )


def downgrade() -> None:
    op.drop_table("access_policy_groups")
    op.drop_table("group_memberships")
    op.drop_table("access_policies")
    op.drop_table("groups")
    op.drop_table("principals")
    op.drop_table("organizations")
