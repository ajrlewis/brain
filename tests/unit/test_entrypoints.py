from unittest.mock import patch

import uvicorn

from brain_api import main as api_main
from brain_mcp import server as mcp_server


def test_api_command_starts_uvicorn() -> None:
    with patch.object(uvicorn, "run") as run:
        api_main.run()

    run.assert_called_once_with("brain_api.app:app", host="0.0.0.0", port=8000)


def test_mcp_command_starts_server() -> None:
    with patch.object(mcp_server.mcp, "run") as run:
        mcp_server.run()

    run.assert_called_once_with()
