from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from brain_auth import AuthContext, AuthorizationDenied
from brain_core import (
    DuplicatePageContent,
    InvalidKnowledgeReference,
    KnowledgeNotFound,
    VersionConflict,
)
from brain_core.knowledge import KnowledgeService
from brain_db import Folder, Page, PageVersion, PageVersionSource, Source
from brain_schemas import FolderCreate, PageCreate, PageVersionCreate, ProvenanceInput, SourceCreate

ORG = UUID("10000000-0000-0000-0000-000000000001")
OTHER_ORG = UUID("10000000-0000-0000-0000-000000000002")
PRINCIPAL = UUID("20000000-0000-0000-0000-000000000001")
GROUP = UUID("30000000-0000-0000-0000-000000000001")
OPEN_POLICY = UUID("40000000-0000-0000-0000-000000000001")
RESTRICTED_POLICY = UUID("40000000-0000-0000-0000-000000000002")


class FakeKnowledgeRepository:
    policies: dict[UUID, set[UUID]]
    folder_records: dict[UUID, Folder]
    sources: dict[UUID, Source]
    page_records: dict[UUID, Page]
    page_versions: list[PageVersion]
    links: list[PageVersionSource]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @classmethod
    def reset(cls) -> None:
        cls.policies = {OPEN_POLICY: set(), RESTRICTED_POLICY: {GROUP}}
        cls.folder_records = {}
        cls.sources = {}
        cls.page_records = {}
        cls.page_versions = []
        cls.links = []

    async def policy_group_ids(self, organization_id: UUID, policy_id: UUID) -> set[UUID] | None:
        return self.policies.get(policy_id) if organization_id == ORG else None

    async def principal_exists(self, organization_id: UUID, principal_id: UUID) -> bool:
        return organization_id == ORG and principal_id == PRINCIPAL

    async def context_is_valid(
        self, organization_id: UUID, principal_id: UUID, group_ids: frozenset[UUID]
    ) -> bool:
        return organization_id == ORG and principal_id == PRINCIPAL

    async def get_folder(self, organization_id: UUID, folder_id: UUID) -> Folder | None:
        folder = self.folder_records.get(folder_id)
        return folder if folder is not None and folder.organization_id == organization_id else None

    async def add_folder(self, folder: Folder) -> None:
        self._generated(folder)
        self.folder_records[folder.id] = folder

    async def folders(self, organization_id: UUID) -> list[Folder]:
        return [
            folder
            for folder in self.folder_records.values()
            if folder.organization_id == organization_id
        ]

    async def get_source(self, organization_id: UUID, source_id: UUID) -> Source | None:
        source = self.sources.get(source_id)
        return source if source is not None and source.organization_id == organization_id else None

    async def add_source(self, source: Source) -> None:
        self._generated(source)
        self.sources[source.id] = source

    async def source_inventory(self, organization_id: UUID) -> list[Source]:
        return [
            source for source in self.sources.values() if source.organization_id == organization_id
        ]

    async def get_page(
        self, organization_id: UUID, page_id: UUID, *, lock: bool = False
    ) -> Page | None:
        page = self.page_records.get(page_id)
        return page if page is not None and page.organization_id == organization_id else None

    async def add_page(self, page: Page) -> None:
        self._generated(page)
        self.page_records[page.id] = page

    async def pages(self, organization_id: UUID) -> list[Page]:
        return [
            page
            for page in self.page_records.values()
            if page.organization_id == organization_id and page.current_version_id is not None
        ]

    async def page_inventory(self, organization_id: UUID) -> list[tuple[Page, UUID, str]]:
        return [
            (page, version.id, version.content_hash)
            for page in await self.pages(organization_id)
            for version in self.page_versions
            if version.id == page.current_version_id
        ]

    async def add_version(self, version: PageVersion) -> None:
        version.id = uuid4()
        version.created_at = datetime.now(UTC)
        self.page_versions.append(version)

    async def add_version_source(self, link: PageVersionSource) -> None:
        self.links.append(link)

    async def versions(self, page_id: UUID) -> list[PageVersion]:
        return [version for version in self.page_versions if version.page_id == page_id]

    async def next_version(self, page_id: UUID) -> int:
        return len([version for version in self.page_versions if version.page_id == page_id]) + 1

    async def provenance(self, version_id: UUID) -> list[tuple[PageVersionSource, Source]]:
        return [
            (link, self.sources[link.source_id])
            for link in self.links
            if link.page_version_id == version_id
        ]

    @staticmethod
    def _generated(record: Folder | Source | Page) -> None:
        now = datetime.now(UTC)
        record.id = uuid4()
        record.created_at = now
        record.updated_at = now


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> KnowledgeService:
    FakeKnowledgeRepository.reset()
    monkeypatch.setattr("brain_core.knowledge.KnowledgeRepository", FakeKnowledgeRepository)
    return KnowledgeService(lambda: AsyncMock(spec=AsyncSession))


@pytest.fixture
def context() -> AuthContext:
    return AuthContext(organization_id=ORG, principal_id=PRINCIPAL, group_ids=frozenset({GROUP}))


async def test_folder_and_source_create_read_and_reference_failures(
    service: KnowledgeService, context: AuthContext
) -> None:
    folder = await service.create_folder(
        context,
        FolderCreate(
            slug="portfolio", name="Portfolio", access_policy_id=OPEN_POLICY, steward_id=PRINCIPAL
        ),
    )
    child = await service.create_folder(
        context,
        FolderCreate(
            slug="active",
            name="Active",
            parent_id=folder.id,
            access_policy_id=OPEN_POLICY,
            steward_id=PRINCIPAL,
        ),
    )
    assert (await service.get_folder(context, child.id)).parent_id == folder.id

    source = await service.create_source(
        context,
        SourceCreate(
            source_type="memo",
            title="Synthetic memo",
            status="active",
            access_policy_id=OPEN_POLICY,
            steward_id=PRINCIPAL,
            metadata={"format": "markdown"},
        ),
    )
    assert (await service.get_source(context, source.id)).metadata == {"format": "markdown"}
    assert [item.id for item in await service.list_sources(context)] == [source.id]

    with pytest.raises(InvalidKnowledgeReference):
        await service.create_folder(
            context,
            FolderCreate(
                slug="bad",
                name="Bad",
                parent_id=uuid4(),
                access_policy_id=OPEN_POLICY,
                steward_id=PRINCIPAL,
            ),
        )
    with pytest.raises(InvalidKnowledgeReference):
        await service.create_source(
            context,
            SourceCreate(
                source_type="memo",
                title="Bad",
                status="active",
                access_policy_id=uuid4(),
                steward_id=PRINCIPAL,
            ),
        )
    with pytest.raises(KnowledgeNotFound):
        await service.get_source(context, uuid4())


async def test_page_versions_authorization_and_hidden_provenance(
    service: KnowledgeService, context: AuthContext
) -> None:
    parent = await service.create_folder(
        context,
        FolderCreate(
            slug="portfolio",
            name="Portfolio",
            access_policy_id=OPEN_POLICY,
            steward_id=PRINCIPAL,
        ),
    )
    folder = await service.create_folder(
        context,
        FolderCreate(
            slug="active",
            name="Active",
            parent_id=parent.id,
            access_policy_id=OPEN_POLICY,
            steward_id=PRINCIPAL,
        ),
    )
    source = await service.create_source(
        context,
        SourceCreate(
            source_type="memo",
            title="Memo",
            status="active",
            access_policy_id=OPEN_POLICY,
            steward_id=PRINCIPAL,
        ),
    )
    request = PageCreate(
        slug="orion",
        title="Orion",
        content_markdown="# Orion\n\nInitial fact.",
        access_policy_id=OPEN_POLICY,
        steward_id=PRINCIPAL,
        folder_id=folder.id,
        sources=[ProvenanceInput(source_id=source.id, relationship="derived_from")],
    )
    page = await service.create_page(context, request)
    assert page.current_version.version == 1
    assert len(page.current_version.provenance) == 1
    assert (await service.list_pages(context))[0].path == "/portfolio/active/orion"
    assert (await service.get_page_by_path(context, "/portfolio/active/orion")).id == page.id
    with pytest.raises(KnowledgeNotFound):
        await service.get_page_by_path(context, "/missing")

    updated = await service.create_page_version(
        context,
        page.id,
        PageVersionCreate(
            expected_current_version_id=page.current_version.id,
            content_markdown="# Orion\n\nSuperseding fact.",
            sources=[ProvenanceInput(source_id=source.id, relationship="corroborated_by")],
        ),
    )
    assert updated.current_version.version == 2
    assert [version.version for version in updated.versions] == [1, 2]

    with pytest.raises(VersionConflict):
        await service.create_page_version(
            context,
            page.id,
            PageVersionCreate(
                expected_current_version_id=page.current_version.id,
                content_markdown="# Orion\n\nStale edit.",
            ),
        )
    assert len(FakeKnowledgeRepository.page_versions) == 2
    assert updated.versions[0].content_markdown == request.content_markdown

    with pytest.raises(DuplicatePageContent):
        await service.create_page_version(
            context,
            page.id,
            PageVersionCreate(
                expected_current_version_id=updated.current_version.id,
                content_markdown="# Orion\n\nSuperseding fact.",
            ),
        )

    duplicate = await service.create_page(
        context,
        PageCreate(
            slug="orion-copy",
            title="Orion copy",
            content_markdown=updated.current_version.content_markdown,
            access_policy_id=OPEN_POLICY,
            steward_id=PRINCIPAL,
        ),
    )
    exact_hashes = [
        item.content_hash
        for item in await service.list_pages(context)
        if item.id in {page.id, duplicate.id}
    ]
    assert len(exact_hashes) == 2
    assert len(set(exact_hashes)) == 1

    FakeKnowledgeRepository.sources[source.id].access_policy_id = RESTRICTED_POLICY
    outsider = AuthContext(organization_id=ORG, principal_id=PRINCIPAL, group_ids=frozenset())
    visible_page = await service.get_page(outsider, page.id)
    assert visible_page.current_version.provenance == []
    with pytest.raises(AuthorizationDenied):
        await service.get_source(outsider, source.id)

    FakeKnowledgeRepository.page_records[page.id].access_policy_id = RESTRICTED_POLICY
    FakeKnowledgeRepository.page_records[duplicate.id].access_policy_id = RESTRICTED_POLICY
    assert await service.list_pages(outsider) == []
    with pytest.raises(AuthorizationDenied):
        await service.get_page(outsider, page.id)
    with pytest.raises(AuthorizationDenied):
        await service.get_page(
            AuthContext(organization_id=OTHER_ORG, principal_id=PRINCIPAL, group_ids=frozenset()),
            page.id,
        )


async def test_large_inventory_does_not_read_page_version_bodies(
    service: KnowledgeService,
    context: AuthContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    for index in range(500):
        page_id = uuid4()
        version_id = uuid4()
        FakeKnowledgeRepository.page_records[page_id] = Page(
            id=page_id,
            organization_id=ORG,
            slug=f"page-{index}",
            title=f"Page {index}",
            current_version_id=version_id,
            access_policy_id=OPEN_POLICY,
            position=index,
            steward_id=PRINCIPAL,
            created_by_id=PRINCIPAL,
            updated_by_id=PRINCIPAL,
            created_at=now,
            updated_at=now,
        )
        FakeKnowledgeRepository.page_versions.append(
            PageVersion(
                id=version_id,
                organization_id=ORG,
                page_id=page_id,
                version=1,
                content_markdown=f"# Page {index}\n\nLarge body that inventory must not return.",
                content_hash=f"{index:064x}",
                created_by_id=PRINCIPAL,
                created_at=now,
            )
        )

    async def fail_if_versions_are_loaded(
        repository: FakeKnowledgeRepository, page_id: UUID
    ) -> list[PageVersion]:
        raise AssertionError("inventory loaded immutable PageVersion bodies")

    monkeypatch.setattr(FakeKnowledgeRepository, "versions", fail_if_versions_are_loaded)

    inventory = await service.list_pages(context)

    assert len(inventory) == 500
    assert inventory[0].model_dump().keys() == {
        "id",
        "slug",
        "title",
        "path",
        "current_version_id",
        "content_hash",
    }


async def test_page_creation_rejects_wrong_tenant_references(
    service: KnowledgeService, context: AuthContext
) -> None:
    request = PageCreate(
        slug="invalid",
        title="Invalid",
        content_markdown="# Invalid",
        access_policy_id=OPEN_POLICY,
        steward_id=PRINCIPAL,
        folder_id=uuid4(),
    )
    with pytest.raises(InvalidKnowledgeReference):
        await service.create_page(context, request)

    request.folder_id = None
    request.sources = [ProvenanceInput(source_id=uuid4(), relationship="derived_from")]
    with pytest.raises(InvalidKnowledgeReference):
        await service.create_page(context, request)
