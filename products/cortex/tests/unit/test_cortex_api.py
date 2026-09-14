from fastapi.testclient import TestClient

from cortex_api import create_app


def test_health() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "cortex-api", "status": "ok"}
