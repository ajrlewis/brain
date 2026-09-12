from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Transport-neutral health contract."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok"] = "ok"
    service: str
    environment: str
