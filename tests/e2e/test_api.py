from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from brain_api import create_app
from brain_auth import AuthContext, LocalBearerAuthenticator
from brain_core import HealthService, KnowledgeNotFound, KnowledgeService, Settings
from brain_schemas import FolderCreate, FolderResponse, HealthResponse


class RecordingHealthService(HealthService):
    def __init__(self) -> None:
        super().__init__(service_name="shared-test-service", settings=Settings(environment="test"))
        self.calls = 0

    def check(self) -> HealthResponse:
        self.calls += 1
        return super().check()


class FolderKnowledgeService(KnowledgeService):
    def __init__(self, folder: FolderResponse) -> None:
        self.folder = folder

    async def create_folder(self, context: AuthContext, request: FolderCreate) -> FolderResponse:
        return self.folder

    async def get_folder(self, context: AuthContext, folder_id: UUID) -> FolderResponse:
        raise KnowledgeNotFound("Folder was not found")


class UnavailableKnowledgeService(FolderKnowledgeService):
    async def create_folder(self, context: AuthContext, request: FolderCreate) -> FolderResponse:
        raise SQLAlchemyTimeoutError("pool exhausted")


class HttpClient(Protocol):
    def get(self, url: str, *, headers: dict[str, str] | None = None) -> Response: ...

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: object | None = None,
    ) -> Response: ...


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


def test_http_knowledge_routes_are_thin_authenticated_adapters() -> None:
    context = AuthContext(
        organization_id=UUID("10000000-0000-0000-0000-000000000001"),
        principal_id=UUID("20000000-0000-0000-0000-000000000001"),
        group_ids=frozenset(),
    )
    now = datetime.now(UTC)
    folder_id = UUID("50000000-0000-0000-0000-000000000001")
    policy_id = UUID("40000000-0000-0000-0000-000000000001")
    folder = FolderResponse(
        id=folder_id,
        organization_id=context.organization_id,
        parent_id=None,
        kind="page",
        slug="knowledge",
        name="Knowledge",
        description=None,
        access_policy_id=policy_id,
        position=0,
        steward_id=context.principal_id,
        created_at=now,
        updated_at=now,
    )
    knowledge = FolderKnowledgeService(folder)
    app = create_app(
        knowledge_service=knowledge,
        authenticator=LocalBearerAuthenticator(token="secret", context=context),
    )
    client = cast(HttpClient, TestClient(app))
    headers = {"Authorization": "Bearer secret"}

    created = client.post(
        "/folders",
        headers=headers,
        json={
            "slug": "knowledge",
            "name": "Knowledge",
            "access_policy_id": str(policy_id),
            "steward_id": str(context.principal_id),
        },
    )
    missing = client.get(f"/folders/{folder_id}", headers=headers)

    assert created.status_code == 201
    assert created.json()["id"] == str(folder_id)
    assert missing.status_code == 404


def test_http_database_timeout_is_a_controlled_failure() -> None:
    context = AuthContext(
        UUID("10000000-0000-0000-0000-000000000001"),
        UUID("20000000-0000-0000-0000-000000000001"),
        frozenset(),
    )
    now = datetime.now(UTC)
    folder = FolderResponse(
        id=UUID("50000000-0000-0000-0000-000000000001"),
        organization_id=context.organization_id,
        parent_id=None,
        kind="page",
        slug="knowledge",
        name="Knowledge",
        description=None,
        access_policy_id=UUID("40000000-0000-0000-0000-000000000001"),
        position=0,
        steward_id=context.principal_id,
        created_at=now,
        updated_at=now,
    )
    app = create_app(
        knowledge_service=UnavailableKnowledgeService(folder),
        authenticator=LocalBearerAuthenticator(token="secret", context=context),
    )
    client = cast(HttpClient, TestClient(app))

    response = client.post(
        "/folders",
        headers={"Authorization": "Bearer secret"},
        json={
            "slug": "knowledge",
            "name": "Knowledge",
            "access_policy_id": "40000000-0000-0000-0000-000000000001",
            "steward_id": str(context.principal_id),
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Database operation unavailable"}
