from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from brain_auth import AuthContext, AuthorizationDenied
from brain_core import DuplicatePageContent, InvalidKnowledgeReference, KnowledgeNotFound
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
    folders: dict[UUID, Folder]
    sources: dict[UUID, Source]
    pages: dict[UUID, Page]
    page_versions: list[PageVersion]
    links: list[PageVersionSource]

    def __init__(self, session: Session) -> None:
        self.session = session

    @classmethod
    def reset(cls) -> None:
        cls.policies = {OPEN_POLICY: set(), RESTRICTED_POLICY: {GROUP}}
        cls.folders = {}
        cls.sources = {}
        cls.pages = {}
        cls.page_versions = []
        cls.links = []

    def policy_group_ids(self, organization_id: UUID, policy_id: UUID) -> set[UUID] | None:
        return self.policies.get(policy_id) if organization_id == ORG else None

    def principal_exists(self, organization_id: UUID, principal_id: UUID) -> bool:
        return organization_id == ORG and principal_id == PRINCIPAL

    def context_is_valid(
        self, organization_id: UUID, principal_id: UUID, group_ids: frozenset[UUID]
    ) -> bool:
        return organization_id == ORG and principal_id == PRINCIPAL

    def get_folder(self, organization_id: UUID, folder_id: UUID) -> Folder | None:
        folder = self.folders.get(folder_id)
        return folder if folder is not None and folder.organization_id == organization_id else None

    def add_folder(self, folder: Folder) -> None:
        self._generated(folder)
        self.folders[folder.id] = folder

    def get_source(self, organization_id: UUID, source_id: UUID) -> Source | None:
        source = self.sources.get(source_id)
        return source if source is not None and source.organization_id == organization_id else None

    def add_source(self, source: Source) -> None:
        self._generated(source)
        self.sources[source.id] = source

    def get_page(self, organization_id: UUID, page_id: UUID, *, lock: bool = False) -> Page | None:
        page = self.pages.get(page_id)
        return page if page is not None and page.organization_id == organization_id else None

    def add_page(self, page: Page) -> None:
        self._generated(page)
        self.pages[page.id] = page

    def add_version(self, version: PageVersion) -> None:
        version.id = uuid4()
        version.created_at = datetime.now(UTC)
        self.page_versions.append(version)

    def add_version_source(self, link: PageVersionSource) -> None:
        self.links.append(link)

    def versions(self, page_id: UUID) -> list[PageVersion]:
        return [version for version in self.page_versions if version.page_id == page_id]

    def next_version(self, page_id: UUID) -> int:
        return len(self.versions(page_id)) + 1

    def provenance(self, version_id: UUID) -> list[tuple[PageVersionSource, Source]]:
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
    return KnowledgeService(lambda: Mock(spec=Session))


@pytest.fixture
def context() -> AuthContext:
    return AuthContext(organization_id=ORG, principal_id=PRINCIPAL, group_ids=frozenset({GROUP}))


def test_folder_and_source_create_read_and_reference_failures(
    service: KnowledgeService, context: AuthContext
) -> None:
    folder = service.create_folder(
        context,
        FolderCreate(
            slug="portfolio", name="Portfolio", access_policy_id=OPEN_POLICY, steward_id=PRINCIPAL
        ),
    )
    child = service.create_folder(
        context,
        FolderCreate(
            slug="active",
            name="Active",
            parent_id=folder.id,
            access_policy_id=OPEN_POLICY,
            steward_id=PRINCIPAL,
        ),
    )
    assert service.get_folder(context, child.id).parent_id == folder.id

    source = service.create_source(
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
    assert service.get_source(context, source.id).metadata == {"format": "markdown"}

    with pytest.raises(InvalidKnowledgeReference):
        service.create_folder(
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
        service.create_source(
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
        service.get_source(context, uuid4())


def test_page_versions_authorization_and_hidden_provenance(
    service: KnowledgeService, context: AuthContext
) -> None:
    source = service.create_source(
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
        sources=[ProvenanceInput(source_id=source.id, relationship="derived_from")],
    )
    page = service.create_page(context, request)
    assert page.current_version.version == 1
    assert len(page.current_version.provenance) == 1

    updated = service.create_page_version(
        context,
        page.id,
        PageVersionCreate(
            content_markdown="# Orion\n\nSuperseding fact.",
            sources=[ProvenanceInput(source_id=source.id, relationship="corroborated_by")],
        ),
    )
    assert updated.current_version.version == 2
    assert [version.version for version in updated.versions] == [1, 2]
    assert updated.versions[0].content_markdown == request.content_markdown

    with pytest.raises(DuplicatePageContent):
        service.create_page_version(
            context,
            page.id,
            PageVersionCreate(content_markdown="# Orion\n\nSuperseding fact."),
        )

    FakeKnowledgeRepository.sources[source.id].access_policy_id = RESTRICTED_POLICY
    outsider = AuthContext(organization_id=ORG, principal_id=PRINCIPAL, group_ids=frozenset())
    visible_page = service.get_page(outsider, page.id)
    assert visible_page.current_version.provenance == []
    with pytest.raises(AuthorizationDenied):
        service.get_source(outsider, source.id)

    FakeKnowledgeRepository.pages[page.id].access_policy_id = RESTRICTED_POLICY
    with pytest.raises(AuthorizationDenied):
        service.get_page(outsider, page.id)
    with pytest.raises(AuthorizationDenied):
        service.get_page(
            AuthContext(organization_id=OTHER_ORG, principal_id=PRINCIPAL, group_ids=frozenset()),
            page.id,
        )


def test_page_creation_rejects_wrong_tenant_references(
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
        service.create_page(context, request)

    request.folder_id = None
    request.sources = [ProvenanceInput(source_id=uuid4(), relationship="derived_from")]
    with pytest.raises(InvalidKnowledgeReference):
        service.create_page(context, request)
