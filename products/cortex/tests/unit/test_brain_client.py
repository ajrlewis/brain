import json
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from cortex_brain import (
    BrainClient,
    BrainHealth,
    BrainIdentityContext,
    BrainMalformedResponse,
    BrainRejectedCredentials,
    BrainUnavailable,
    BrainUnexpectedResponse,
)

BASE_URL = "http://brain.test"
TOKEN = "synthetic-secret"
IDENTITY = {
    "organization_id": "10000000-0000-0000-0000-000000000001",
    "principal_id": "20000000-0000-0000-0000-000000000001",
    "group_ids": ["30000000-0000-0000-0000-000000000001"],
}


def client_for(handler: httpx.AsyncBaseTransport) -> BrainClient:
    return BrainClient(
        base_url=BASE_URL,
        api_key=TOKEN,
        connect_timeout_seconds=0.1,
        read_timeout_seconds=0.2,
        http_client=httpx.AsyncClient(transport=handler, base_url=BASE_URL),
    )


@pytest.mark.parametrize("method", ["health", "identity_context"])
async def test_successful_reads_are_typed_and_bearer_is_used_only_for_identity(
    method: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            assert "authorization" not in request.headers
            return httpx.Response(
                200, json={"status": "ok", "service": "brain-api", "environment": "test"}
            )
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        return httpx.Response(200, json=IDENTITY)

    client = client_for(httpx.MockTransport(handler))
    result = await getattr(client, method)()

    assert isinstance(result, BrainHealth | BrainIdentityContext)


@pytest.mark.parametrize("status_code", [401, 403])
async def test_authorization_denial_is_distinct(status_code: int) -> None:
    client = client_for(httpx.MockTransport(lambda _: httpx.Response(status_code)))

    with pytest.raises(BrainRejectedCredentials, match="rejected") as caught:
        await client.identity_context()

    assert TOKEN not in str(caught.value)


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (httpx.ConnectError("offline"), BrainUnavailable),
        (httpx.ReadTimeout("slow"), BrainUnavailable),
    ],
)
async def test_transport_failures_are_unavailable(
    failure: Exception, expected: type[Exception]
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise failure

    with pytest.raises(expected, match="unavailable"):
        await client_for(httpx.MockTransport(handler)).health()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"status": "wrong"}),
    ],
)
async def test_malformed_success_responses_are_rejected(response: httpx.Response) -> None:
    client = client_for(httpx.MockTransport(lambda _: response))

    with pytest.raises(BrainMalformedResponse, match="malformed"):
        await client.health()


async def test_unexpected_status_is_distinct() -> None:
    client = client_for(httpx.MockTransport(lambda _: httpx.Response(500, text=TOKEN)))

    with pytest.raises(BrainUnexpectedResponse, match="unexpected") as caught:
        await client.health()

    assert TOKEN not in str(caught.value)


async def test_client_closes_the_http_client_it_owns() -> None:
    client = BrainClient(
        base_url=BASE_URL,
        api_key=TOKEN,
        connect_timeout_seconds=0.1,
        read_timeout_seconds=0.2,
    )

    await client.aclose()


def test_published_brain_contract_contains_typed_client_operations() -> None:
    contract_path = Path(__file__).parents[3] / "brain/apps/web/openapi.json"
    contract = json.loads(contract_path.read_text())
    schemas = contract["components"]["schemas"]

    operations = {
        "/health": BrainHealth,
        "/auth/context": BrainIdentityContext,
    }
    for path, model in operations.items():
        response_schema = contract["paths"][path]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        published_name = response_schema["$ref"].rsplit("/", 1)[-1]
        model_schema = model.model_json_schema()
        published_schema = schemas[published_name]
        assert set(model_schema["properties"]) == set(published_schema["properties"])
        assert set(published_schema["required"]) <= set(model_schema["required"])

    assert BrainHealth.model_validate(
        {"status": "ok", "service": "brain-api", "environment": "test"}
    )
    assert BrainIdentityContext.model_validate(IDENTITY).principal_id == UUID(
        IDENTITY["principal_id"]
    )


def test_cortex_runtime_does_not_import_brain_implementation_or_persistence() -> None:
    cortex_root = Path(__file__).parents[2]
    cortex_files = [
        *cortex_root.glob("apps/api/src/**/*.py"),
        *cortex_root.glob("packages/*/src/**/*.py"),
    ]
    cortex_runtime = "\n".join(path.read_text() for path in cortex_files)
    for forbidden in ("brain_schemas", "brain_auth", "brain_core", "brain_db"):
        assert forbidden not in cortex_runtime

    brain_client = "\n".join(
        path.read_text() for path in cortex_root.glob("packages/brain/src/**/*.py")
    )
    for forbidden in ("sqlalchemy", "psycopg", "cortex_state"):
        assert forbidden not in brain_client

    brain_root = cortex_root.parent / "brain"
    brain_runtime = "\n".join(
        path.read_text()
        for path in [
            *brain_root.glob("apps/*/src/**/*.py"),
            *brain_root.glob("packages/*/src/**/*.py"),
        ]
    )
    assert "cortex_" not in brain_runtime
