from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from brain_db.models import (
    AccessPolicy,
    AccessPolicyGroup,
    Folder,
    Group,
    GroupMembership,
    Page,
    PageVersion,
    PageVersionSource,
    Principal,
    Source,
)


class Repository:
    """Base for repositories participating in a caller-owned unit of work."""

    def __init__(self, session: Session) -> None:
        self.session = session


class KnowledgeRepository(Repository):
    """Persistence operations for a caller-owned knowledge unit of work."""

    def policy_group_ids(self, organization_id: UUID, policy_id: UUID) -> set[UUID] | None:
        policy = self.session.scalar(
            select(AccessPolicy.id).where(
                AccessPolicy.id == policy_id,
                AccessPolicy.organization_id == organization_id,
                AccessPolicy.deleted_at.is_(None),
            )
        )
        if policy is None:
            return None
        return set(
            self.session.scalars(
                select(AccessPolicyGroup.group_id).where(
                    AccessPolicyGroup.organization_id == organization_id,
                    AccessPolicyGroup.access_policy_id == policy_id,
                )
            )
        )

    def principal_exists(self, organization_id: UUID, principal_id: UUID) -> bool:
        return (
            self.session.scalar(
                select(Principal.id).where(
                    Principal.id == principal_id,
                    Principal.organization_id == organization_id,
                    Principal.is_active.is_(True),
                    Principal.deleted_at.is_(None),
                )
            )
            is not None
        )

    def context_is_valid(
        self, organization_id: UUID, principal_id: UUID, group_ids: frozenset[UUID]
    ) -> bool:
        if not self.principal_exists(organization_id, principal_id):
            return False
        if not group_ids:
            return True
        valid_group_ids = set(
            self.session.scalars(
                select(Group.id)
                .join(
                    GroupMembership,
                    (GroupMembership.organization_id == Group.organization_id)
                    & (GroupMembership.group_id == Group.id),
                )
                .where(
                    Group.organization_id == organization_id,
                    Group.id.in_(group_ids),
                    Group.deleted_at.is_(None),
                    GroupMembership.principal_id == principal_id,
                )
            )
        )
        return valid_group_ids == set(group_ids)

    def get_folder(self, organization_id: UUID, folder_id: UUID) -> Folder | None:
        return self.session.scalar(
            select(Folder).where(
                Folder.id == folder_id,
                Folder.organization_id == organization_id,
                Folder.deleted_at.is_(None),
            )
        )

    def add_folder(self, folder: Folder) -> None:
        self.session.add(folder)
        self.session.flush()

    def get_source(self, organization_id: UUID, source_id: UUID) -> Source | None:
        return self.session.scalar(
            select(Source).where(
                Source.id == source_id,
                Source.organization_id == organization_id,
                Source.deleted_at.is_(None),
            )
        )

    def add_source(self, source: Source) -> None:
        self.session.add(source)
        self.session.flush()

    def get_page(self, organization_id: UUID, page_id: UUID, *, lock: bool = False) -> Page | None:
        query = select(Page).where(
            Page.id == page_id,
            Page.organization_id == organization_id,
            Page.deleted_at.is_(None),
        )
        return self.session.scalar(query.with_for_update() if lock else query)

    def add_page(self, page: Page) -> None:
        self.session.add(page)
        self.session.flush()

    def add_version(self, version: PageVersion) -> None:
        self.session.add(version)
        self.session.flush()

    def add_version_source(self, link: PageVersionSource) -> None:
        self.session.add(link)

    def versions(self, page_id: UUID) -> list[PageVersion]:
        return list(
            self.session.scalars(
                select(PageVersion)
                .where(PageVersion.page_id == page_id)
                .order_by(PageVersion.version)
            )
        )

    def next_version(self, page_id: UUID) -> int:
        return (
            self.session.scalar(
                select(func.coalesce(func.max(PageVersion.version), 0)).where(
                    PageVersion.page_id == page_id
                )
            )
            or 0
        ) + 1

    def provenance(self, version_id: UUID) -> list[tuple[PageVersionSource, Source]]:
        return list(
            self.session.execute(
                select(PageVersionSource, Source)
                .join(
                    Source,
                    (Source.id == PageVersionSource.source_id)
                    & (Source.organization_id == PageVersionSource.organization_id),
                )
                .where(
                    PageVersionSource.page_version_id == version_id,
                    Source.deleted_at.is_(None),
                )
                .order_by(Source.id, PageVersionSource.relationship)
            ).tuples()
        )
