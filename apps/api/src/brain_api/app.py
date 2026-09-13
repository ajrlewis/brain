from collections.abc import Callable
from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastmcp import FastMCP

from brain_api.auth import get_auth_context
from brain_auth import AuthContext, AuthorizationDenied, LocalBearerAuthenticator
from brain_core import (
    DuplicatePageContent,
    HealthService,
    IdentityService,
    InvalidKnowledgeReference,
    KnowledgeConflict,
    KnowledgeNotFound,
    KnowledgeService,
    Settings,
    SkillConflict,
    SkillNotFound,
    SkillService,
    VersionConflict,
    create_knowledge_service,
    create_local_authenticator,
    create_skill_service,
)
from brain_core.settings import get_settings
from brain_mcp import create_server
from brain_schemas import (
    AuthContextResponse,
    FolderCreate,
    FolderResponse,
    HealthResponse,
    InvalidSkillDocument,
    PageCreate,
    PageInventoryItem,
    PageResponse,
    PageVersionCreate,
    SkillCreate,
    SkillInventoryItem,
    SkillResponse,
    SkillVersionCreate,
    SourceCreate,
    SourceInventoryItem,
    SourceResponse,
)


def get_health_service(request: Request) -> HealthService:
    return cast(HealthService, request.app.state.health_service)


def create_app(
    *,
    settings: Settings | None = None,
    health_service: HealthService | None = None,
    identity_service: IdentityService | None = None,
    knowledge_service: KnowledgeService | None = None,
    skill_service: SkillService | None = None,
    authenticator: LocalBearerAuthenticator | None = None,
    mcp_server: FastMCP | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_health_service = health_service or HealthService(
        service_name="brain-api",
        settings=resolved_settings,
    )
    resolved_identity_service = identity_service or IdentityService()
    resolved_knowledge_service = knowledge_service or create_knowledge_service(resolved_settings)
    resolved_skill_service = skill_service or create_skill_service(resolved_settings)
    resolved_authenticator = authenticator or create_local_authenticator(resolved_settings)
    resolved_mcp_server = mcp_server or create_server(
        settings=resolved_settings,
        health_service=resolved_health_service,
        identity_service=resolved_identity_service,
        knowledge_service=resolved_knowledge_service,
        skill_service=resolved_skill_service,
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
    app.state.knowledge_service = resolved_knowledge_service
    app.state.skill_service = resolved_skill_service
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

    @app.post("/folders", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
    def create_folder(
        request: FolderCreate,
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> FolderResponse:
        return call_knowledge(resolved_knowledge_service.create_folder, context, request)

    @app.get("/folders/{folder_id}", response_model=FolderResponse)
    def get_folder(
        folder_id: UUID,
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> FolderResponse:
        return call_knowledge(resolved_knowledge_service.get_folder, context, folder_id)

    @app.post("/sources", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
    def create_source(
        request: SourceCreate,
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> SourceResponse:
        return call_knowledge(resolved_knowledge_service.create_source, context, request)

    @app.get("/sources/{source_id}", response_model=SourceResponse)
    def get_source(
        source_id: UUID,
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> SourceResponse:
        return call_knowledge(resolved_knowledge_service.get_source, context, source_id)

    @app.get("/sources", response_model=list[SourceInventoryItem])
    def list_sources(
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> list[SourceInventoryItem]:
        return call_knowledge(resolved_knowledge_service.list_sources, context)

    @app.post("/pages", response_model=PageResponse, status_code=status.HTTP_201_CREATED)
    def create_page(
        request: PageCreate,
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> PageResponse:
        return call_knowledge(resolved_knowledge_service.create_page, context, request)

    @app.get("/pages", response_model=list[PageInventoryItem])
    def list_pages(
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> list[PageInventoryItem]:
        return call_knowledge(resolved_knowledge_service.list_pages, context)

    @app.get("/pages/by-path/{page_path:path}", response_model=PageResponse)
    def get_page_by_path(
        page_path: str,
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> PageResponse:
        return call_knowledge(resolved_knowledge_service.get_page_by_path, context, page_path)

    @app.get("/pages/{page_id}", response_model=PageResponse)
    def get_page(
        page_id: UUID,
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> PageResponse:
        return call_knowledge(resolved_knowledge_service.get_page, context, page_id)

    @app.post(
        "/pages/{page_id}/versions",
        response_model=PageResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_page_version(
        page_id: UUID,
        request: PageVersionCreate,
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> PageResponse:
        return call_knowledge(
            resolved_knowledge_service.create_page_version, context, page_id, request
        )

    @app.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
    def create_skill(
        request: SkillCreate,
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> SkillResponse:
        return call_knowledge(resolved_skill_service.create_skill, context, request)

    @app.get("/skills", response_model=list[SkillInventoryItem])
    def list_skills(
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> list[SkillInventoryItem]:
        return call_knowledge(resolved_skill_service.list_skills, context)

    @app.get("/skills/by-slug/{slug}", response_model=SkillResponse)
    def get_skill_by_slug(
        slug: str,
        context: Annotated[AuthContext, Depends(get_auth_context)],
        version: int | None = None,
    ) -> SkillResponse:
        return call_knowledge(resolved_skill_service.get_skill_by_slug, context, slug, version)

    @app.get("/skills/{skill_id}", response_model=SkillResponse)
    def get_skill(
        skill_id: UUID,
        context: Annotated[AuthContext, Depends(get_auth_context)],
        version: int | None = None,
    ) -> SkillResponse:
        return call_knowledge(resolved_skill_service.get_skill, context, skill_id, version)

    @app.post(
        "/skills/{skill_id}/versions",
        response_model=SkillResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_skill_version(
        skill_id: UUID,
        request: SkillVersionCreate,
        context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> SkillResponse:
        return call_knowledge(
            resolved_skill_service.create_skill_version, context, skill_id, request
        )

    app.mount("/mcp", mcp_app, name="mcp")

    return app


def call_knowledge[**P, R](function: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    try:
        return function(*args, **kwargs)
    except KnowledgeNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except AuthorizationDenied as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (InvalidKnowledgeReference, DuplicatePageContent, KnowledgeConflict) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except SkillNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (SkillConflict, VersionConflict) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except InvalidSkillDocument as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


app = create_app()
