from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from brain_db.models import (
    AccessPolicy,
    AccessPolicyGroup,
    Chunk,
    Folder,
    Group,
    GroupMembership,
    Page,
    PageVersion,
    PageVersionSource,
    Principal,
    Skill,
    SkillVersion,
    Source,
)


class Repository:
    """Base for repositories participating in a caller-owned unit of work."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session


class KnowledgeRepository(Repository):
    """Persistence operations for a caller-owned knowledge unit of work."""

    async def policy_group_ids(self, organization_id: UUID, policy_id: UUID) -> set[UUID] | None:
        policy = await self.session.scalar(
            select(AccessPolicy.id).where(
                AccessPolicy.id == policy_id,
                AccessPolicy.organization_id == organization_id,
                AccessPolicy.deleted_at.is_(None),
            )
        )
        if policy is None:
            return None
        return set(
            await self.session.scalars(
                select(AccessPolicyGroup.group_id).where(
                    AccessPolicyGroup.organization_id == organization_id,
                    AccessPolicyGroup.access_policy_id == policy_id,
                )
            )
        )

    async def principal_exists(self, organization_id: UUID, principal_id: UUID) -> bool:
        return (
            await self.session.scalar(
                select(Principal.id).where(
                    Principal.id == principal_id,
                    Principal.organization_id == organization_id,
                    Principal.is_active.is_(True),
                    Principal.deleted_at.is_(None),
                )
            )
            is not None
        )

    async def context_is_valid(
        self, organization_id: UUID, principal_id: UUID, group_ids: frozenset[UUID]
    ) -> bool:
        if not await self.principal_exists(organization_id, principal_id):
            return False
        if not group_ids:
            return True
        valid_group_ids = set(
            await self.session.scalars(
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

    async def get_folder(self, organization_id: UUID, folder_id: UUID) -> Folder | None:
        return await self.session.scalar(
            select(Folder).where(
                Folder.id == folder_id,
                Folder.organization_id == organization_id,
                Folder.deleted_at.is_(None),
            )
        )

    async def folders(self, organization_id: UUID) -> list[Folder]:
        return list(
            await self.session.scalars(
                select(Folder).where(
                    Folder.organization_id == organization_id,
                    Folder.deleted_at.is_(None),
                )
            )
        )

    async def add_folder(self, folder: Folder) -> None:
        self.session.add(folder)
        await self.session.flush()

    async def get_source(self, organization_id: UUID, source_id: UUID) -> Source | None:
        return await self.session.scalar(
            select(Source).where(
                Source.id == source_id,
                Source.organization_id == organization_id,
                Source.deleted_at.is_(None),
            )
        )

    async def add_source(self, source: Source) -> None:
        self.session.add(source)
        await self.session.flush()

    async def source_inventory(self, organization_id: UUID) -> list[Source]:
        return list(
            await self.session.scalars(
                select(Source)
                .where(
                    Source.organization_id == organization_id,
                    Source.deleted_at.is_(None),
                )
                .order_by(Source.title, Source.id)
            )
        )

    async def get_page(
        self, organization_id: UUID, page_id: UUID, *, lock: bool = False
    ) -> Page | None:
        query = select(Page).where(
            Page.id == page_id,
            Page.organization_id == organization_id,
            Page.deleted_at.is_(None),
        )
        return await self.session.scalar(query.with_for_update() if lock else query)

    async def add_page(self, page: Page) -> None:
        self.session.add(page)
        await self.session.flush()

    async def pages(self, organization_id: UUID) -> list[Page]:
        return list(
            await self.session.scalars(
                select(Page)
                .where(
                    Page.organization_id == organization_id,
                    Page.deleted_at.is_(None),
                    Page.current_version_id.is_not(None),
                )
                .order_by(Page.position, Page.slug)
            )
        )

    async def page_inventory(self, organization_id: UUID) -> list[tuple[Page, UUID, str]]:
        return list(
            (
                await self.session.execute(
                    select(Page, PageVersion.id, PageVersion.content_hash)
                    .join(
                        PageVersion,
                        (PageVersion.page_id == Page.id)
                        & (PageVersion.id == Page.current_version_id),
                    )
                    .where(
                        Page.organization_id == organization_id,
                        Page.deleted_at.is_(None),
                    )
                    .order_by(Page.position, Page.slug)
                )
            ).tuples()
        )

    async def add_version(self, version: PageVersion) -> None:
        self.session.add(version)
        await self.session.flush()

    async def replace_chunks(self, page_version_id: UUID, chunks: list[Chunk]) -> None:
        await self.session.execute(delete(Chunk).where(Chunk.page_version_id == page_version_id))
        self.session.add_all(chunks)
        await self.session.flush()

    async def add_version_source(self, link: PageVersionSource) -> None:
        self.session.add(link)

    async def versions(self, page_id: UUID) -> list[PageVersion]:
        return list(
            await self.session.scalars(
                select(PageVersion)
                .where(PageVersion.page_id == page_id)
                .order_by(PageVersion.version)
            )
        )

    async def next_version(self, page_id: UUID) -> int:
        return (
            await self.session.scalar(
                select(func.coalesce(func.max(PageVersion.version), 0)).where(
                    PageVersion.page_id == page_id
                )
            )
            or 0
        ) + 1

    async def provenance(self, version_id: UUID) -> list[tuple[PageVersionSource, Source]]:
        return list(
            (
                await self.session.execute(
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
                )
            ).tuples()
        )


class SkillRepository(KnowledgeRepository):
    """Persistence operations for a caller-owned Skill unit of work."""

    async def get_skill(
        self, organization_id: UUID, skill_id: UUID, *, lock: bool = False
    ) -> Skill | None:
        query = select(Skill).where(
            Skill.id == skill_id,
            Skill.organization_id == organization_id,
            Skill.deleted_at.is_(None),
        )
        return await self.session.scalar(query.with_for_update() if lock else query)

    async def get_skill_by_slug(self, organization_id: UUID, slug: str) -> Skill | None:
        return await self.session.scalar(
            select(Skill).where(
                Skill.organization_id == organization_id,
                Skill.slug == slug,
                Skill.deleted_at.is_(None),
            )
        )

    async def skills(self, organization_id: UUID) -> list[Skill]:
        return list(
            await self.session.scalars(
                select(Skill)
                .where(
                    Skill.organization_id == organization_id,
                    Skill.deleted_at.is_(None),
                    Skill.current_version_id.is_not(None),
                )
                .order_by(Skill.position, Skill.slug)
            )
        )

    async def skill_inventory(self, organization_id: UUID) -> list[tuple[Skill, UUID, str]]:
        return list(
            (
                await self.session.execute(
                    select(Skill, SkillVersion.id, SkillVersion.content_hash)
                    .join(
                        SkillVersion,
                        (SkillVersion.skill_id == Skill.id)
                        & (SkillVersion.id == Skill.current_version_id),
                    )
                    .where(
                        Skill.organization_id == organization_id,
                        Skill.deleted_at.is_(None),
                    )
                    .order_by(Skill.position, Skill.slug)
                )
            ).tuples()
        )

    async def add_skill(self, skill: Skill) -> None:
        self.session.add(skill)
        await self.session.flush()

    async def add_skill_version(self, version: SkillVersion) -> None:
        self.session.add(version)
        await self.session.flush()

    async def skill_versions(self, skill_id: UUID) -> list[SkillVersion]:
        return list(
            await self.session.scalars(
                select(SkillVersion)
                .where(SkillVersion.skill_id == skill_id)
                .order_by(SkillVersion.version)
            )
        )

    async def next_skill_version(self, skill_id: UUID) -> int:
        return (
            await self.session.scalar(
                select(func.coalesce(func.max(SkillVersion.version), 0)).where(
                    SkillVersion.skill_id == skill_id
                )
            )
            or 0
        ) + 1
