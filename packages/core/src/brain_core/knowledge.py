from hashlib import sha256
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from brain_auth import AuthContext, AuthorizationDenied, require_access
from brain_core.settings import Settings
from brain_db import (
    Folder,
    KnowledgeRepository,
    Page,
    PageVersion,
    PageVersionSource,
    SessionFactory,
    Source,
    create_engine,
    create_session_factory,
    session_scope,
)
from brain_schemas import (
    FolderCreate,
    FolderResponse,
    PageCreate,
    PageResponse,
    PageVersionCreate,
    PageVersionResponse,
    ProvenanceInput,
    ProvenanceResponse,
    SourceCreate,
    SourceResponse,
)


class KnowledgeNotFound(Exception):
    """Raised when a live same-tenant knowledge record does not exist."""


class DuplicatePageContent(Exception):
    """Raised when content is already present in a Page's immutable history."""


class KnowledgeConflict(Exception):
    """Raised when knowledge violates a uniqueness or structural constraint."""


class InvalidKnowledgeReference(Exception):
    """Raised when a referenced same-tenant record is absent or invalid."""


class KnowledgeService:
    """Govern knowledge through one shared HTTP/MCP application boundary."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self.session_factory = session_factory

    def create_folder(self, context: AuthContext, request: FolderCreate) -> FolderResponse:
        with session_scope(self.session_factory) as session:
            repository = KnowledgeRepository(session)
            self._require_context(repository, context)
            self._require_principal(repository, context, request.steward_id)
            self._require_policy(repository, context, request.access_policy_id)
            if request.parent_id is not None:
                parent = repository.get_folder(context.organization_id, request.parent_id)
                if parent is None:
                    raise InvalidKnowledgeReference("Parent folder was not found")
                self._require_resource(repository, context, parent.access_policy_id)
            folder = Folder(
                organization_id=context.organization_id,
                parent_id=request.parent_id,
                kind="page",
                slug=request.slug,
                name=request.name,
                description=request.description,
                access_policy_id=request.access_policy_id,
                position=request.position,
                steward_id=request.steward_id,
                created_by_id=context.principal_id,
                updated_by_id=context.principal_id,
            )
            try:
                repository.add_folder(folder)
            except IntegrityError as error:
                raise KnowledgeConflict("Folder conflicts with an existing record") from error
            return self._folder_response(folder)

    def get_folder(self, context: AuthContext, folder_id: UUID) -> FolderResponse:
        with session_scope(self.session_factory) as session:
            repository = KnowledgeRepository(session)
            self._require_context(repository, context)
            folder = repository.get_folder(context.organization_id, folder_id)
            if folder is None:
                raise KnowledgeNotFound("Folder was not found")
            self._require_resource(repository, context, folder.access_policy_id)
            return self._folder_response(folder)

    def create_source(self, context: AuthContext, request: SourceCreate) -> SourceResponse:
        with session_scope(self.session_factory) as session:
            repository = KnowledgeRepository(session)
            self._require_context(repository, context)
            self._require_principal(repository, context, request.steward_id)
            self._require_policy(repository, context, request.access_policy_id)
            source = Source(
                organization_id=context.organization_id,
                source_type=request.source_type,
                title=request.title,
                canonical_uri=request.canonical_uri,
                external_id=request.external_id,
                status=request.status,
                access_policy_id=request.access_policy_id,
                metadata_=request.metadata,
                provenance=request.provenance,
                created_by_id=context.principal_id,
                updated_by_id=context.principal_id,
                steward_id=request.steward_id,
            )
            try:
                repository.add_source(source)
            except IntegrityError as error:
                raise KnowledgeConflict("Source conflicts with an existing record") from error
            return self._source_response(source)

    def get_source(self, context: AuthContext, source_id: UUID) -> SourceResponse:
        with session_scope(self.session_factory) as session:
            repository = KnowledgeRepository(session)
            self._require_context(repository, context)
            source = repository.get_source(context.organization_id, source_id)
            if source is None:
                raise KnowledgeNotFound("Source was not found")
            self._require_resource(repository, context, source.access_policy_id)
            return self._source_response(source)

    def create_page(self, context: AuthContext, request: PageCreate) -> PageResponse:
        with session_scope(self.session_factory) as session:
            repository = KnowledgeRepository(session)
            self._require_context(repository, context)
            self._validate_page_references(repository, context, request)
            self._validate_sources(repository, context, request.sources)
            page = Page(
                organization_id=context.organization_id,
                folder_id=request.folder_id,
                slug=request.slug,
                title=request.title,
                access_policy_id=request.access_policy_id,
                position=request.position,
                steward_id=request.steward_id,
                created_by_id=context.principal_id,
                updated_by_id=context.principal_id,
            )
            try:
                repository.add_page(page)
            except IntegrityError as error:
                raise KnowledgeConflict("Page conflicts with an existing record") from error
            try:
                version = self._insert_version(
                    repository, context, page, request.content_markdown, request.sources
                )
            except IntegrityError as error:
                raise KnowledgeConflict("Page version conflicts with existing history") from error
            page.current_version_id = version.id
            session.flush()
            return self._page_response(repository, context, page)

    def create_page_version(
        self, context: AuthContext, page_id: UUID, request: PageVersionCreate
    ) -> PageResponse:
        with session_scope(self.session_factory) as session:
            repository = KnowledgeRepository(session)
            self._require_context(repository, context)
            page = repository.get_page(context.organization_id, page_id, lock=True)
            if page is None:
                raise KnowledgeNotFound("Page was not found")
            self._require_resource(repository, context, page.access_policy_id)
            self._validate_sources(repository, context, request.sources)
            content_hash = sha256(request.content_markdown.encode()).hexdigest()
            if any(
                version.content_hash == content_hash for version in repository.versions(page.id)
            ):
                raise DuplicatePageContent("This content already exists for the Page")
            try:
                version = self._insert_version(
                    repository, context, page, request.content_markdown, request.sources
                )
            except IntegrityError as error:
                raise KnowledgeConflict("Page version conflicts with existing history") from error
            page.current_version_id = version.id
            page.updated_by_id = context.principal_id
            session.flush()
            return self._page_response(repository, context, page)

    def get_page(self, context: AuthContext, page_id: UUID) -> PageResponse:
        with session_scope(self.session_factory) as session:
            repository = KnowledgeRepository(session)
            self._require_context(repository, context)
            page = repository.get_page(context.organization_id, page_id)
            if page is None or page.current_version_id is None:
                raise KnowledgeNotFound("Page was not found")
            self._require_resource(repository, context, page.access_policy_id)
            return self._page_response(repository, context, page)

    def _insert_version(
        self,
        repository: KnowledgeRepository,
        context: AuthContext,
        page: Page,
        markdown: str,
        provenance: list[ProvenanceInput],
    ) -> PageVersion:
        version = PageVersion(
            organization_id=context.organization_id,
            page_id=page.id,
            version=repository.next_version(page.id),
            content_markdown=markdown,
            content_hash=sha256(markdown.encode()).hexdigest(),
            created_by_id=context.principal_id,
        )
        repository.add_version(version)
        for item in provenance:
            repository.add_version_source(
                PageVersionSource(
                    organization_id=context.organization_id,
                    page_version_id=version.id,
                    source_id=item.source_id,
                    relationship=item.relationship,
                    metadata_=item.metadata,
                )
            )
        repository.session.flush()
        return version

    def _page_response(
        self, repository: KnowledgeRepository, context: AuthContext, page: Page
    ) -> PageResponse:
        shaped = [
            self._version_response(repository, context, version)
            for version in repository.versions(page.id)
        ]
        current = next(item for item in shaped if item.id == page.current_version_id)
        return PageResponse(
            id=page.id,
            organization_id=page.organization_id,
            folder_id=page.folder_id,
            slug=page.slug,
            title=page.title,
            access_policy_id=page.access_policy_id,
            position=page.position,
            steward_id=page.steward_id,
            created_at=page.created_at,
            updated_at=page.updated_at,
            current_version=current,
            versions=shaped,
        )

    def _version_response(
        self, repository: KnowledgeRepository, context: AuthContext, version: PageVersion
    ) -> PageVersionResponse:
        provenance: list[ProvenanceResponse] = []
        for link, source in repository.provenance(version.id):
            groups = repository.policy_group_ids(context.organization_id, source.access_policy_id)
            if groups is None:
                continue
            try:
                require_access(
                    context,
                    organization_id=source.organization_id,
                    permitted_group_ids=groups,
                )
            except AuthorizationDenied:
                continue
            provenance.append(
                ProvenanceResponse(
                    source=self._source_response(source),
                    relationship=link.relationship,
                    metadata=link.metadata_,
                )
            )
        return PageVersionResponse(
            id=version.id,
            page_id=version.page_id,
            version=version.version,
            content_markdown=version.content_markdown,
            content_hash=version.content_hash,
            created_by_id=version.created_by_id,
            created_at=version.created_at,
            provenance=provenance,
        )

    def _validate_page_references(
        self, repository: KnowledgeRepository, context: AuthContext, request: PageCreate
    ) -> None:
        self._require_principal(repository, context, request.steward_id)
        self._require_policy(repository, context, request.access_policy_id)
        if request.folder_id is not None:
            folder = repository.get_folder(context.organization_id, request.folder_id)
            if folder is None:
                raise InvalidKnowledgeReference("Folder was not found")
            self._require_resource(repository, context, folder.access_policy_id)

    def _validate_sources(
        self,
        repository: KnowledgeRepository,
        context: AuthContext,
        provenance: list[ProvenanceInput],
    ) -> None:
        for item in provenance:
            source = repository.get_source(context.organization_id, item.source_id)
            if source is None:
                raise InvalidKnowledgeReference("Source was not found")
            self._require_resource(repository, context, source.access_policy_id)

    @staticmethod
    def _require_context(repository: KnowledgeRepository, context: AuthContext) -> None:
        if not repository.context_is_valid(
            context.organization_id, context.principal_id, context.group_ids
        ):
            raise AuthorizationDenied("The caller's authorization context is not valid")

    @staticmethod
    def _require_principal(
        repository: KnowledgeRepository, context: AuthContext, principal_id: UUID
    ) -> None:
        if not repository.principal_exists(context.organization_id, principal_id):
            raise InvalidKnowledgeReference("Principal was not found")

    @staticmethod
    def _require_policy(
        repository: KnowledgeRepository, context: AuthContext, policy_id: UUID
    ) -> None:
        groups = repository.policy_group_ids(context.organization_id, policy_id)
        if groups is None:
            raise InvalidKnowledgeReference("Access policy was not found")
        require_access(context, organization_id=context.organization_id, permitted_group_ids=groups)

    @staticmethod
    def _require_resource(
        repository: KnowledgeRepository, context: AuthContext, policy_id: UUID
    ) -> None:
        groups = repository.policy_group_ids(context.organization_id, policy_id)
        if groups is None:
            raise KnowledgeNotFound("Resource was not found")
        require_access(context, organization_id=context.organization_id, permitted_group_ids=groups)

    @staticmethod
    def _folder_response(folder: Folder) -> FolderResponse:
        return FolderResponse(
            id=folder.id,
            organization_id=folder.organization_id,
            parent_id=folder.parent_id,
            kind=folder.kind,
            slug=folder.slug,
            name=folder.name,
            description=folder.description,
            access_policy_id=folder.access_policy_id,
            position=folder.position,
            steward_id=folder.steward_id,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )

    @staticmethod
    def _source_response(source: Source) -> SourceResponse:
        return SourceResponse(
            id=source.id,
            organization_id=source.organization_id,
            source_type=source.source_type,
            title=source.title,
            canonical_uri=source.canonical_uri,
            external_id=source.external_id,
            status=source.status,
            access_policy_id=source.access_policy_id,
            steward_id=source.steward_id,
            metadata=source.metadata_,
            provenance=source.provenance,
            created_at=source.created_at,
            updated_at=source.updated_at,
        )


def create_knowledge_service(settings: Settings) -> KnowledgeService:
    """Build the database-backed service without opening a database connection."""
    engine = create_engine(settings)
    return KnowledgeService(create_session_factory(engine))
