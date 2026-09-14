from collections.abc import Awaitable, Callable
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from sqlalchemy.exc import SQLAlchemyError

from brain_auth import (
    AuthContext,
    AuthenticationError,
    AuthorizationDenied,
    LocalBearerAuthenticator,
)
from brain_core import (
    DuplicatePageContent,
    HealthService,
    IdentityService,
    InvalidKnowledgeReference,
    KnowledgeConflict,
    KnowledgeNotFound,
    KnowledgeService,
    SearchService,
    Settings,
    SkillConflict,
    SkillNotFound,
    SkillService,
    VersionConflict,
    create_knowledge_service,
    create_local_authenticator,
    create_persistence_services,
    create_search_service,
    create_skill_service,
)
from brain_core.settings import get_settings
from brain_schemas import (
    AuthContextResponse,
    FolderCreate,
    FolderResponse,
    HealthResponse,
    InvalidSkillDocument,
    PageCreate,
    PageInventoryItem,
    PageResponse,
    PageVersionCreate,
    SearchRequest,
    SearchResponse,
    SkillCreate,
    SkillInventoryItem,
    SkillResponse,
    SkillVersionCreate,
    SourceCreate,
    SourceInventoryItem,
    SourceResponse,
)


def create_server(
    *,
    settings: Settings | None = None,
    health_service: HealthService | None = None,
    identity_service: IdentityService | None = None,
    knowledge_service: KnowledgeService | None = None,
    skill_service: SkillService | None = None,
    search_service: SearchService | None = None,
    authenticator: LocalBearerAuthenticator | None = None,
) -> FastMCP:
    resolved_settings = settings or get_settings()
    service = health_service or HealthService(
        service_name="brain-mcp",
        settings=resolved_settings,
    )
    resolved_identity_service = identity_service or IdentityService()
    if knowledge_service is None and skill_service is None and search_service is None:
        (
            resolved_knowledge_service,
            resolved_skill_service,
            resolved_search_service,
        ) = create_persistence_services(resolved_settings)
    else:
        resolved_knowledge_service = knowledge_service or create_knowledge_service(
            resolved_settings
        )
        resolved_skill_service = skill_service or create_skill_service(resolved_settings)
        resolved_search_service = search_service or create_search_service(resolved_settings)
    resolved_authenticator = authenticator or create_local_authenticator(resolved_settings)
    server = FastMCP(name="Brain")

    @server.tool
    def health() -> HealthResponse:
        """Report whether the Brain MCP interface is available."""
        return service.check()

    @server.tool
    def auth_context() -> AuthContextResponse:
        """Return the caller's provider-neutral authorization context."""
        try:
            context = resolved_authenticator.authenticate(get_http_headers().get("authorization"))
        except AuthenticationError as error:
            raise ToolError(str(error)) from error
        return resolved_identity_service.describe(context)

    def authenticated() -> AuthContext:
        try:
            return resolved_authenticator.authenticate(get_http_headers().get("authorization"))
        except AuthenticationError as error:
            raise ToolError(str(error)) from error

    @server.tool
    async def create_folder(request: FolderCreate) -> FolderResponse:
        """Create a governed Page folder."""
        return await call_knowledge(
            resolved_knowledge_service.create_folder, authenticated(), request
        )

    @server.tool
    async def get_folder(folder_id: UUID) -> FolderResponse:
        """Read an authorized live Page folder."""
        return await call_knowledge(
            resolved_knowledge_service.get_folder, authenticated(), folder_id
        )

    @server.tool
    async def create_source(request: SourceCreate) -> SourceResponse:
        """Create Source identity and structured provenance metadata."""
        return await call_knowledge(
            resolved_knowledge_service.create_source, authenticated(), request
        )

    @server.tool
    async def get_source(source_id: UUID) -> SourceResponse:
        """Read an independently authorized live Source."""
        return await call_knowledge(
            resolved_knowledge_service.get_source, authenticated(), source_id
        )

    @server.tool
    async def list_sources() -> list[SourceInventoryItem]:
        """List authorized live Source identities and freshness fields."""
        return await call_knowledge(resolved_knowledge_service.list_sources, authenticated())

    @server.tool
    async def create_page(request: PageCreate) -> PageResponse:
        """Create a Page with its first immutable Markdown version."""
        return await call_knowledge(
            resolved_knowledge_service.create_page, authenticated(), request
        )

    @server.tool
    async def get_page(page_id: UUID) -> PageResponse:
        """Read an authorized Page, versions, and visible provenance."""
        return await call_knowledge(resolved_knowledge_service.get_page, authenticated(), page_id)

    @server.tool
    async def list_pages() -> list[PageInventoryItem]:
        """List authorized live Pages with stable paths and current hashes."""
        return await call_knowledge(resolved_knowledge_service.list_pages, authenticated())

    @server.tool
    async def get_page_by_path(path: str) -> PageResponse:
        """Read an authorized live Page by its stable folder/Page path."""
        return await call_knowledge(
            resolved_knowledge_service.get_page_by_path, authenticated(), path
        )

    @server.tool
    async def create_page_version(page_id: UUID, request: PageVersionCreate) -> PageResponse:
        """Append an immutable Page version and make it current."""
        return await call_knowledge(
            resolved_knowledge_service.create_page_version, authenticated(), page_id, request
        )

    @server.tool
    async def create_skill(request: SkillCreate) -> SkillResponse:
        """Create a Skill with its first validated immutable document."""
        return await call_knowledge(resolved_skill_service.create_skill, authenticated(), request)

    @server.tool
    async def list_skills() -> list[SkillInventoryItem]:
        """List authorized live Skills and their current content hashes."""
        return await call_knowledge(resolved_skill_service.list_skills, authenticated())

    @server.tool
    async def get_skill(skill_id: UUID, version: int | None = None) -> SkillResponse:
        """Read an authorized Skill, optionally selecting an immutable version."""
        return await call_knowledge(
            resolved_skill_service.get_skill, authenticated(), skill_id, version
        )

    @server.tool
    async def get_skill_by_slug(slug: str, version: int | None = None) -> SkillResponse:
        """Read an authorized Skill by stable slug."""
        return await call_knowledge(
            resolved_skill_service.get_skill_by_slug, authenticated(), slug, version
        )

    @server.tool
    async def create_skill_version(skill_id: UUID, request: SkillVersionCreate) -> SkillResponse:
        """Append a validated Skill document if its reviewed base is still current."""
        return await call_knowledge(
            resolved_skill_service.create_skill_version, authenticated(), skill_id, request
        )

    @server.tool
    async def search(request: SearchRequest) -> SearchResponse:
        """Search authorized current Page versions with hybrid retrieval."""
        return await call_knowledge(resolved_search_service.search, authenticated(), request)

    return server


async def call_knowledge[**P, R](
    function: Callable[P, Awaitable[R]], *args: P.args, **kwargs: P.kwargs
) -> R:
    try:
        return await function(*args, **kwargs)
    except (
        AuthorizationDenied,
        DuplicatePageContent,
        InvalidKnowledgeReference,
        KnowledgeConflict,
        KnowledgeNotFound,
        SkillConflict,
        SkillNotFound,
        VersionConflict,
        InvalidSkillDocument,
    ) as error:
        raise ToolError(str(error)) from error
    except SQLAlchemyError as error:
        raise ToolError("Database operation unavailable") from error


mcp = create_server()


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
