from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers

from brain_auth import AuthenticationError, LocalBearerAuthenticator
from brain_core import HealthService, IdentityService, Settings, create_local_authenticator
from brain_core.settings import get_settings
from brain_schemas import AuthContextResponse, HealthResponse


def create_server(
    *,
    settings: Settings | None = None,
    health_service: HealthService | None = None,
    identity_service: IdentityService | None = None,
    authenticator: LocalBearerAuthenticator | None = None,
) -> FastMCP:
    resolved_settings = settings or get_settings()
    service = health_service or HealthService(
        service_name="brain-mcp",
        settings=resolved_settings,
    )
    resolved_identity_service = identity_service or IdentityService()
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

    return server


mcp = create_server()


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
