"""Export Brain's FastAPI contract for deterministic web schema generation."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for source in (
    "apps/api/src",
    "apps/mcp/src",
    "packages/auth/src",
    "packages/core/src",
    "packages/db/src",
    "packages/schemas/src",
):
    sys.path.insert(0, str(ROOT / source))

os.environ.setdefault("ENVIRONMENT", "test")

from brain_api.app import create_app  # noqa: E402

output = Path(__file__).resolve().parents[1] / "openapi.json"
output.write_text(json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n")
