from typing import Protocol, cast
from uuid import UUID

from fastapi.testclient import TestClient
from httpx import Response

from brain_api import create_app
from brain_auth import AuthContext, LocalBearerAuthenticator
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
    def get(self, url: str, *, headers: dict[str, str] | None = None) -> Response: ...


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


def test_http_auth_context_allows_valid_token_and_denies_missing_token() -> None:
    context = AuthContext(
        organization_id=UUID("10000000-0000-0000-0000-000000000001"),
        principal_id=UUID("20000000-0000-0000-0000-000000000001"),
        group_ids=frozenset({UUID("30000000-0000-0000-0000-000000000001")}),
    )
    app = create_app(authenticator=LocalBearerAuthenticator(token="local-secret", context=context))
    client = cast(HttpClient, TestClient(app))

    denied = client.get("/auth/context")
    allowed = client.get("/auth/context", headers={"Authorization": "Bearer local-secret"})

    assert denied.status_code == 401
    assert denied.headers["www-authenticate"] == "Bearer"
    assert allowed.status_code == 200
    assert allowed.json() == {
        "organization_id": str(context.organization_id),
        "principal_id": str(context.principal_id),
        "group_ids": [str(group_id) for group_id in context.group_ids],
    }
