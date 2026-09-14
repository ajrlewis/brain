from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from brain_db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="slug_format"),
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(63), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class Principal(TimestampMixin, Base):
    __tablename__ = "principals"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "external_subject"),
        CheckConstraint("kind IN ('user', 'service', 'agent')", name="kind_allowed"),
        CheckConstraint("length(btrim(display_name)) > 0", name="display_name_not_blank"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    external_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Group(TimestampMixin, Base):
    __tablename__ = "groups"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "slug"),
        CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="slug_format"),
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(63), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class GroupMembership(Base):
    __tablename__ = "group_memberships"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "group_id", "principal_id"),
        ForeignKeyConstraint(
            ["organization_id", "group_id"],
            ["groups.organization_id", "groups.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "principal_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="CASCADE",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))
    group_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))
    principal_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AccessPolicy(TimestampMixin, Base):
    __tablename__ = "access_policies"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "name"),
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class AccessPolicyGroup(Base):
    __tablename__ = "access_policy_groups"
    __table_args__ = (
        PrimaryKeyConstraint("organization_id", "access_policy_id", "group_id"),
        ForeignKeyConstraint(
            ["organization_id", "access_policy_id"],
            ["access_policies.organization_id", "access_policies.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "group_id"],
            ["groups.organization_id", "groups.id"],
            ondelete="CASCADE",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))
    access_policy_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))
    group_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))


class Folder(TimestampMixin, Base):
    __tablename__ = "folders"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "id", "kind"),
        UniqueConstraint(
            "organization_id",
            "parent_id",
            "kind",
            "slug",
            name="uq_folders_sibling_slug",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint("kind = 'page'", name="kind_page_only"),
        CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="slug_format"),
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
        ForeignKeyConstraint(
            ["organization_id", "parent_id", "kind"],
            ["folders.organization_id", "folders.id", "folders.kind"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "access_policy_id"],
            ["access_policies.organization_id", "access_policies.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "steward_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "updated_by_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    parent_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="page")
    slug: Mapped[str] = mapped_column(String(63), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    access_policy_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    steward_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    created_by_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    updated_by_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)


class Source(TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        Index(
            "uq_sources_external_identity",
            "organization_id",
            "source_type",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        CheckConstraint("length(btrim(source_type)) > 0", name="source_type_not_blank"),
        CheckConstraint("length(btrim(title)) > 0", name="title_not_blank"),
        CheckConstraint("length(btrim(status)) > 0", name="status_not_blank"),
        CheckConstraint("jsonb_typeof(metadata) = 'object'", name="metadata_object"),
        CheckConstraint("jsonb_typeof(provenance) = 'object'", name="provenance_object"),
        ForeignKeyConstraint(
            ["organization_id", "access_policy_id"],
            ["access_policies.organization_id", "access_policies.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "updated_by_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "steward_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_uri: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(255), nullable=False)
    access_policy_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_by_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    updated_by_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    steward_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)


class Page(TimestampMixin, Base):
    __tablename__ = "pages"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "slug"),
        CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="slug_format"),
        CheckConstraint("length(btrim(title)) > 0", name="title_not_blank"),
        ForeignKeyConstraint(
            ["organization_id", "folder_id"],
            ["folders.organization_id", "folders.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "access_policy_id"],
            ["access_policies.organization_id", "access_policies.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "steward_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "updated_by_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["current_version_id", "id"],
            ["page_versions.id", "page_versions.page_id"],
            use_alter=True,
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    folder_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    slug: Mapped[str] = mapped_column(String(63), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    current_version_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    access_policy_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    steward_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    created_by_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    updated_by_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)


class PageVersion(Base):
    __tablename__ = "page_versions"
    __table_args__ = (
        UniqueConstraint("id", "page_id"),
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("page_id", "version"),
        UniqueConstraint("page_id", "content_hash"),
        CheckConstraint("version > 0", name="version_positive"),
        CheckConstraint("length(btrim(content_markdown)) > 0", name="content_not_blank"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="content_hash_sha256"),
        ForeignKeyConstraint(
            ["organization_id", "page_id"],
            ["pages.organization_id", "pages.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    page_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Chunk(Base):
    """Regenerable retrieval data attributed to one immutable PageVersion."""

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("page_version_id", "position"),
        Index(
            "ix_chunks_fts",
            text("to_tsvector('english', content)"),
            postgresql_using="gin",
        ),
        Index(
            "ix_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        CheckConstraint("position >= 0", name="position_nonnegative"),
        CheckConstraint("length(btrim(content)) > 0", name="content_not_blank"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="content_hash_sha256"),
        CheckConstraint("jsonb_typeof(heading_path) = 'array'", name="heading_path_array"),
        ForeignKeyConstraint(
            ["organization_id", "page_version_id"],
            ["page_versions.organization_id", "page_versions.id"],
            ondelete="CASCADE",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    page_version_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_path: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PageVersionSource(Base):
    __tablename__ = "page_version_sources"
    __table_args__ = (
        PrimaryKeyConstraint("page_version_id", "source_id", "relationship"),
        CheckConstraint("length(btrim(relationship)) > 0", name="relationship_not_blank"),
        CheckConstraint("jsonb_typeof(metadata) = 'object'", name="metadata_object"),
        ForeignKeyConstraint(
            ["organization_id", "page_version_id"],
            ["page_versions.organization_id", "page_versions.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_id"],
            ["sources.organization_id", "sources.id"],
            ondelete="RESTRICT",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    page_version_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))
    source_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True))
    relationship: Mapped[str] = mapped_column(String(255))
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )


class Skill(TimestampMixin, Base):
    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "slug"),
        CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="slug_format"),
        CheckConstraint("length(btrim(name)) > 0", name="name_not_blank"),
        ForeignKeyConstraint(
            ["organization_id", "folder_id"],
            ["folders.organization_id", "folders.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "access_policy_id"],
            ["access_policies.organization_id", "access_policies.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "steward_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "updated_by_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["current_version_id", "id"],
            ["skill_versions.id", "skill_versions.skill_id"],
            use_alter=True,
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    folder_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    slug: Mapped[str] = mapped_column(String(63), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_version_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    access_policy_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    steward_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    created_by_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    updated_by_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)


class SkillVersion(Base):
    __tablename__ = "skill_versions"
    __table_args__ = (
        UniqueConstraint("id", "skill_id"),
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("skill_id", "version"),
        UniqueConstraint("skill_id", "content_hash"),
        CheckConstraint("version > 0", name="version_positive"),
        CheckConstraint("length(btrim(content_markdown)) > 0", name="content_not_blank"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="content_hash_sha256"),
        ForeignKeyConstraint(
            ["organization_id", "skill_id"],
            ["skills.organization_id", "skills.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_id"],
            ["principals.organization_id", "principals.id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    skill_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
