import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from brain_api import create_app
from brain_core import HealthService, Settings
from brain_mcp import create_server
from brain_schemas import HealthResponse


class RecordingHealthService(HealthService):
    def __init__(self) -> None:
        super().__init__(service_name="shared-test-service", settings=Settings(environment="test"))
        self.calls = 0

    def check(self) -> HealthResponse:
        self.calls += 1
        return super().check()


async def test_mcp_health_uses_injected_shared_service() -> None:
    service = RecordingHealthService()

    async with Client(create_server(health_service=service)) as client:
        result = await client.call_tool("health")

    assert result.structured_content == {
        "status": "ok",
        "service": "shared-test-service",
        "environment": "test",
    }
    assert service.calls == 1


async def test_mcp_health_is_served_by_fastapi() -> None:
    service = RecordingHealthService()
    app = create_app(health_service=service)

    def create_asgi_client(
        headers: dict[str, str] | None = None,
        timeout: httpx.Timeout | None = None,
        auth: httpx.Auth | None = None,
        **kwargs: object,
    ) -> httpx.AsyncClient:
        follow_redirects = kwargs.get("follow_redirects", False)
        assert isinstance(follow_redirects, bool)
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            headers=headers,
            timeout=timeout,
            auth=auth,
            follow_redirects=follow_redirects,
        )

    transport = StreamableHttpTransport(
        "http://testserver/mcp/",
        httpx_client_factory=create_asgi_client,
    )
    async with app.router.lifespan_context(app), Client(transport) as client:
        result = await client.call_tool("health")

    assert result.structured_content == {
        "status": "ok",
        "service": "shared-test-service",
        "environment": "test",
    }
    assert service.calls == 1
