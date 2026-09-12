from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
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
