import os

import httpx
import pytest

pytestmark = pytest.mark.e2e


def test_running_cortex_reaches_deterministic_chat_model() -> None:
    base_url = os.environ.get("CORTEX_TEST_URL")
    if base_url is None:
        pytest.skip("CORTEX_TEST_URL is not configured")

    response = httpx.post(
        f"{base_url}/chat/turn",
        json={"messages": [{"role": "user", "content": "Synthetic integration turn"}]},
        timeout=5,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == {
        "role": "assistant",
        "content": "Synthetic response to: Synthetic integration turn",
    }
    assert body["model"] == "cortex-deterministic-v1"
