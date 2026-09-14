from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    service: Literal["cortex-api"]
    status: Literal["ok"]


def create_app() -> FastAPI:
    app = FastAPI(title="Cortex", version="0.1.0")

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(service="cortex-api", status="ok")

    return app


app = create_app()
