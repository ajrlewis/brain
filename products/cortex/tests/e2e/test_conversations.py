import os

import httpx
import pytest


@pytest.mark.e2e
def test_authenticated_durable_conversation_flow() -> None:
    cortex_url = os.getenv("CORTEX_TEST_URL")
    token = os.getenv("CORTEX_TEST_BEARER_TOKEN", "cortex-local-dev")
    if cortex_url is None:
        pytest.skip("CORTEX_TEST_URL is required for the external Cortex boundary test")
    headers = {"Authorization": f"Bearer {token}"}

    created = httpx.post(f"{cortex_url}/conversations", headers=headers, timeout=10)
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    turn = httpx.post(
        f"{cortex_url}/conversations/{conversation_id}/turns",
        headers=headers,
        json={"content": "Northstar hello"},
        timeout=10,
    )
    assert turn.status_code == 200
    assert turn.json()["model"] == "cortex-deterministic-v1"
    reopened = httpx.get(
        f"{cortex_url}/conversations/{conversation_id}", headers=headers, timeout=10
    )
    assert reopened.status_code == 200
    assert [
        (item["sequence"], item["role"], item["content"]) for item in reopened.json()["messages"]
    ] == [
        (1, "user", "Northstar hello"),
        (2, "assistant", "Synthetic response to: Northstar hello"),
    ]
