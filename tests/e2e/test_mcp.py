import asyncio
from threading import Barrier, get_ident
from uuid import UUID

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from mcp.types import TextContent

from brain_api import create_app
from brain_auth import AuthContext, LocalBearerAuthenticator
from brain_core import HealthService, Settings
from brain_mcp import create_server
from brain_mcp.server import call_knowledge_async
from brain_schemas import HealthResponse


class RecordingHealthService(HealthService):
    def __init__(self) -> None:
        super().__init__(service_name="shared-test-service", settings=Settings(environment="test"))
        self.calls = 0

    def check(self) -> HealthResponse:
        self.calls += 1
        return super().check()


async def test_sync_service_calls_are_offloaded_concurrently() -> None:
    barrier = Barrier(2)
    event_loop_thread = get_ident()

    def blocking_call(value: int) -> tuple[int, int]:
        barrier.wait(timeout=2)
        return value, get_ident()

    results = await asyncio.gather(
        call_knowledge_async(blocking_call, 1),
        call_knowledge_async(blocking_call, 2),
    )

    assert [value for value, _ in results] == [1, 2]
    assert all(thread_id != event_loop_thread for _, thread_id in results)
    assert len({thread_id for _, thread_id in results}) == 2


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


async def test_mcp_auth_context_allows_valid_token_and_denies_missing_token() -> None:
    context = AuthContext(
        organization_id=UUID("10000000-0000-0000-0000-000000000001"),
        principal_id=UUID("20000000-0000-0000-0000-000000000001"),
        group_ids=frozenset({UUID("30000000-0000-0000-0000-000000000001")}),
    )
    app = create_app(authenticator=LocalBearerAuthenticator(token="local-secret", context=context))

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

    denied_transport = StreamableHttpTransport(
        "http://testserver/mcp/", httpx_client_factory=create_asgi_client
    )
    allowed_transport = StreamableHttpTransport(
        "http://testserver/mcp/",
        headers={"Authorization": "Bearer local-secret"},
        httpx_client_factory=create_asgi_client,
    )
    async with app.router.lifespan_context(app):
        async with Client(denied_transport) as client:
            denied = await client.call_tool("auth_context", raise_on_error=False)
        async with Client(allowed_transport) as client:
            allowed = await client.call_tool("auth_context")

    assert denied.is_error is True
    assert isinstance(denied.content[0], TextContent)
    assert "Valid bearer credentials are required" in denied.content[0].text
    assert allowed.structured_content == {
        "organization_id": str(context.organization_id),
        "principal_id": str(context.principal_id),
        "group_ids": [str(group_id) for group_id in context.group_ids],
    }
