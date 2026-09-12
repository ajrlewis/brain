from fastmcp import Client

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
