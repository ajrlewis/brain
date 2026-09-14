from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal, cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cortex_ai import (
    ChatTurnRequest,
    ChatTurnResponse,
    ChatTurnService,
    DeterministicChatModel,
    InvalidChatHistory,
    InvalidModelOutput,
    ModelRejectedRequest,
    ModelTimeout,
    ModelUnavailable,
)
from cortex_api.settings import Settings, get_settings
from cortex_brain import (
    BrainClient,
    BrainMalformedResponse,
    BrainRejectedCredentials,
    BrainUnavailable,
    BrainUnexpectedResponse,
)


class HealthResponse(BaseModel):
    service: Literal["cortex-api"]
    status: Literal["ok"]


class BrainDiagnosticResponse(BaseModel):
    dependency: Literal["brain"] = "brain"
    status: Literal["ok", "disabled", "unauthorized", "malformed", "unavailable", "error"]


def _create_brain_client(settings: Settings) -> BrainClient | None:
    if settings.brain_url is None or settings.brain_api_key is None:
        return None
    return BrainClient(
        base_url=str(settings.brain_url),
        api_key=settings.brain_api_key.get_secret_value(),
        connect_timeout_seconds=settings.brain_connect_timeout_seconds,
        read_timeout_seconds=settings.brain_read_timeout_seconds,
    )


def create_app(
    *,
    settings: Settings | None = None,
    brain_client: BrainClient | None = None,
    chat_service: ChatTurnService | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_client = brain_client or _create_brain_client(resolved_settings)
    resolved_chat_service = chat_service or ChatTurnService(DeterministicChatModel())

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if resolved_client is not None:
            await resolved_client.aclose()

    app = FastAPI(title="Cortex", version="0.1.0", lifespan=lifespan)
    app.state.brain_client = resolved_client
    app.state.chat_service = resolved_chat_service

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, __: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"error": "invalid_request"})

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(service="cortex-api", status="ok")

    @app.post("/chat/turn", response_model=ChatTurnResponse, tags=["chat"])
    async def chat_turn(request: ChatTurnRequest) -> ChatTurnResponse | JSONResponse:
        try:
            return await resolved_chat_service.turn(request)
        except InvalidChatHistory:
            return JSONResponse(status_code=422, content={"error": "history_must_end_with_user"})
        except ModelTimeout:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"error": "model_timeout"},
            )
        except ModelUnavailable:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"error": "model_unavailable"},
            )
        except InvalidModelOutput:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"error": "invalid_model_response"},
            )
        except ModelRejectedRequest:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"error": "model_rejected_request"},
            )
        except Exception:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"error": "model_error"},
            )

    @app.get("/health/brain", response_model=BrainDiagnosticResponse, tags=["system"])
    async def brain_health(request: Request) -> BrainDiagnosticResponse | JSONResponse:
        client = cast(BrainClient | None, request.app.state.brain_client)
        if client is None:
            return JSONResponse(
                status_code=503, content={"dependency": "brain", "status": "disabled"}
            )
        try:
            await client.health()
            await client.identity_context()
        except BrainRejectedCredentials:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"dependency": "brain", "status": "unauthorized"},
            )
        except BrainMalformedResponse:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"dependency": "brain", "status": "malformed"},
            )
        except BrainUnavailable:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"dependency": "brain", "status": "unavailable"},
            )
        except BrainUnexpectedResponse:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"dependency": "brain", "status": "error"},
            )
        return BrainDiagnosticResponse(status="ok")

    return app


app = create_app()
