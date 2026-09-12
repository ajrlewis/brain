from typing import Annotated, cast

from fastapi import Depends, FastAPI, Request
from fastmcp import FastMCP

from brain_api.auth import get_auth_context
from brain_auth import AuthContext, LocalBearerAuthenticator
from brain_core import HealthService, IdentityService, Settings, create_local_authenticator
from brain_core.settings import get_settings
from brain_mcp import create_server
from brain_schemas import AuthContextResponse, HealthResponse


def get_health_service(request: Request) -> HealthService:
    return cast(HealthService, request.app.state.health_service)


def create_app(
    *,
    settings: Settings | None = None,
    health_service: HealthService | None = None,
    identity_service: IdentityService | None = None,
    authenticator: LocalBearerAuthenticator | None = None,
    mcp_server: FastMCP | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_health_service = health_service or HealthService(
        service_name="brain-api",
        settings=resolved_settings,
    )
    resolved_identity_service = identity_service or IdentityService()
    resolved_authenticator = authenticator or create_local_authenticator(resolved_settings)
    resolved_mcp_server = mcp_server or create_server(
        settings=resolved_settings,
        health_service=resolved_health_service,
        identity_service=resolved_identity_service,
        authenticator=resolved_authenticator,
    )
    mcp_app = resolved_mcp_server.http_app(path="/")
    app = FastAPI(
        title="Brain",
        version="0.1.0",
        lifespan=mcp_app.lifespan,
    )
    app.state.health_service = resolved_health_service
    app.state.identity_service = resolved_identity_service
    app.state.authenticator = resolved_authenticator
    app.state.mcp_server = resolved_mcp_server

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health(
        service: Annotated[HealthService, Depends(get_health_service)],
    ) -> HealthResponse:
        return service.check()

    @app.get("/auth/context", response_model=AuthContextResponse, tags=["identity"])
    def auth_context(
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> AuthContextResponse:
        return resolved_identity_service.describe(context)

    app.mount("/mcp", mcp_app, name="mcp")

    return app


app = create_app()
