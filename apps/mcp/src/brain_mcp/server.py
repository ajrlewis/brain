from fastmcp import FastMCP

from brain_core import HealthService, Settings
from brain_core.settings import get_settings
from brain_schemas import HealthResponse


def create_server(
    *,
    settings: Settings | None = None,
    health_service: HealthService | None = None,
) -> FastMCP:
    resolved_settings = settings or get_settings()
    service = health_service or HealthService(
        service_name="brain-mcp",
        settings=resolved_settings,
    )
    server = FastMCP(name="Brain")

    @server.tool
    def health() -> HealthResponse:
        """Report whether the Brain MCP interface is available."""
        return service.check()

    return server


mcp = create_server()


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
