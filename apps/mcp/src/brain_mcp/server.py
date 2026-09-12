from collections.abc import Callable
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers

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
    Settings,
    create_knowledge_service,
    create_local_authenticator,
)
from brain_core.settings import get_settings
from brain_schemas import (
    AuthContextResponse,
    FolderCreate,
    FolderResponse,
    HealthResponse,
    PageCreate,
    PageResponse,
    PageVersionCreate,
    SourceCreate,
    SourceResponse,
)


def create_server(
    *,
    settings: Settings | None = None,
    health_service: HealthService | None = None,
    identity_service: IdentityService | None = None,
    knowledge_service: KnowledgeService | None = None,
    authenticator: LocalBearerAuthenticator | None = None,
) -> FastMCP:
    resolved_settings = settings or get_settings()
    service = health_service or HealthService(
        service_name="brain-mcp",
        settings=resolved_settings,
    )
    resolved_identity_service = identity_service or IdentityService()
    resolved_knowledge_service = knowledge_service or create_knowledge_service(resolved_settings)
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
    def create_folder(request: FolderCreate) -> FolderResponse:
        """Create a governed Page folder."""
        return call_knowledge(resolved_knowledge_service.create_folder, authenticated(), request)

    @server.tool
    def get_folder(folder_id: UUID) -> FolderResponse:
        """Read an authorized live Page folder."""
        return call_knowledge(resolved_knowledge_service.get_folder, authenticated(), folder_id)

    @server.tool
    def create_source(request: SourceCreate) -> SourceResponse:
        """Create Source identity and structured provenance metadata."""
        return call_knowledge(resolved_knowledge_service.create_source, authenticated(), request)

    @server.tool
    def get_source(source_id: UUID) -> SourceResponse:
        """Read an independently authorized live Source."""
        return call_knowledge(resolved_knowledge_service.get_source, authenticated(), source_id)

    @server.tool
    def create_page(request: PageCreate) -> PageResponse:
        """Create a Page with its first immutable Markdown version."""
        return call_knowledge(resolved_knowledge_service.create_page, authenticated(), request)

    @server.tool
    def get_page(page_id: UUID) -> PageResponse:
        """Read an authorized Page, versions, and visible provenance."""
        return call_knowledge(resolved_knowledge_service.get_page, authenticated(), page_id)

    @server.tool
    def create_page_version(page_id: UUID, request: PageVersionCreate) -> PageResponse:
        """Append an immutable Page version and make it current."""
        return call_knowledge(
            resolved_knowledge_service.create_page_version, authenticated(), page_id, request
        )

    return server


def call_knowledge[**P, R](function: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    try:
        return function(*args, **kwargs)
    except (
        AuthorizationDenied,
        DuplicatePageContent,
        InvalidKnowledgeReference,
        KnowledgeConflict,
        KnowledgeNotFound,
    ) as error:
        raise ToolError(str(error)) from error


mcp = create_server()


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
