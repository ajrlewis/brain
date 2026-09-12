from typing import Protocol, cast

from fastapi.testclient import TestClient
from httpx import Response

from brain_api import create_app
from brain_core import HealthService, Settings
from brain_schemas import HealthResponse


class RecordingHealthService(HealthService):
    def __init__(self) -> None:
        super().__init__(service_name="shared-test-service", settings=Settings(environment="test"))
        self.calls = 0

    def check(self) -> HealthResponse:
        self.calls += 1
        return super().check()


class HttpClient(Protocol):
    def get(self, url: str) -> Response: ...


def test_http_health_uses_injected_shared_service() -> None:
    service = RecordingHealthService()
    client = cast(HttpClient, TestClient(create_app(health_service=service)))

    response: Response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "shared-test-service",
        "environment": "test",
    }
    assert service.calls == 1
