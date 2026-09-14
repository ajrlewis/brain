from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from cortex_api import create_app
from cortex_api.settings import Settings
from cortex_brain import BrainClient


def brain_client(handler: httpx.MockTransport) -> BrainClient:
    return BrainClient(
        base_url="http://brain.test",
        api_key="secret",
        connect_timeout_seconds=1,
        read_timeout_seconds=1,
        http_client=httpx.AsyncClient(transport=handler, base_url="http://brain.test"),
    )


def test_health() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "cortex-api", "status": "ok"}


def test_local_health_does_not_call_brain() -> None:
    def fail(_: httpx.Request) -> httpx.Response:
        raise AssertionError("Brain must not be called")

    response = TestClient(create_app(brain_client=brain_client(httpx.MockTransport(fail)))).get(
        "/health"
    )

    assert response.status_code == 200


def test_brain_diagnostic_checks_health_and_identity_without_exposing_identity() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/health":
            return httpx.Response(
                200, json={"status": "ok", "service": "brain-api", "environment": "test"}
            )
        return httpx.Response(
            200,
            json={
                "organization_id": "10000000-0000-0000-0000-000000000001",
                "principal_id": "20000000-0000-0000-0000-000000000001",
                "group_ids": [],
            },
        )

    response = TestClient(create_app(brain_client=brain_client(httpx.MockTransport(handler)))).get(
        "/health/brain"
    )

    assert response.status_code == 200
    assert response.json() == {"dependency": "brain", "status": "ok"}
    assert paths == ["/health", "/auth/context"]


@pytest.mark.parametrize(
    ("upstream_status", "diagnostic_status", "response_status"),
    [(401, "unauthorized", 502), (500, "error", 502)],
)
def test_brain_diagnostic_preserves_upstream_failure_kind(
    upstream_status: int, diagnostic_status: str, response_status: int
) -> None:
    response = TestClient(
        create_app(
            brain_client=brain_client(
                httpx.MockTransport(lambda _: httpx.Response(upstream_status, text="sensitive"))
            )
        )
    ).get("/health/brain")

    assert response.status_code == response_status
    assert response.json() == {"dependency": "brain", "status": diagnostic_status}


@pytest.mark.parametrize(
    ("response_factory", "diagnostic_status", "response_status"),
    [
        (lambda: httpx.Response(200, text="not-json"), "malformed", 502),
        (lambda: httpx.ConnectError("offline"), "unavailable", 503),
    ],
)
def test_brain_diagnostic_maps_malformed_and_unavailable(
    response_factory: Callable[[], httpx.Response | Exception],
    diagnostic_status: str,
    response_status: int,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        result = response_factory()
        if isinstance(result, Exception):
            raise result
        return result

    response = TestClient(create_app(brain_client=brain_client(httpx.MockTransport(handler)))).get(
        "/health/brain"
    )

    assert response.status_code == response_status
    assert response.json() == {"dependency": "brain", "status": diagnostic_status}


def test_brain_diagnostic_reports_disabled_integration() -> None:
    response = TestClient(create_app(settings=Settings())).get("/health/brain")

    assert response.status_code == 503
    assert response.json() == {"dependency": "brain", "status": "disabled"}


def test_partial_brain_configuration_is_invalid() -> None:
    with pytest.raises(ValueError, match="configured together"):
        Settings(brain_url="http://brain.test")


def test_enabled_settings_construct_application_client() -> None:
    app = create_app(
        settings=Settings(brain_url="http://brain.test", brain_api_key="synthetic-secret")
    )

    with TestClient(app):
        assert isinstance(app.state.brain_client, BrainClient)
