from typing import Annotated, cast

from fastapi import Depends, FastAPI, Request

from brain_core import HealthService, Settings
from brain_core.settings import get_settings
from brain_schemas import HealthResponse


def get_health_service(request: Request) -> HealthService:
    return cast(HealthService, request.app.state.health_service)


def create_app(
    *,
    settings: Settings | None = None,
    health_service: HealthService | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(title="Brain", version="0.1.0")
    app.state.health_service = health_service or HealthService(
        service_name="brain-api",
        settings=resolved_settings,
    )

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health(
        service: Annotated[HealthService, Depends(get_health_service)],
    ) -> HealthResponse:
        return service.check()

    return app


app = create_app()
