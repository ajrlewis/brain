import asyncio
import os
from collections.abc import Awaitable
from hashlib import sha256
from time import perf_counter
from typing import Protocol, cast
from uuid import UUID, uuid4

import httpx
import psycopg
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastmcp import Client
from fastmcp.client.client import CallToolResult
from fastmcp.client.transports import StreamableHttpTransport
from httpx import Response
from psycopg.errors import CheckViolation, ForeignKeyViolation, RaiseException, UniqueViolation
from pydantic import PostgresDsn
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from brain_api import create_app
from brain_auth import AuthContext, AuthorizationDenied, LocalBearerAuthenticator
from brain_core import (
    DuplicatePageContent,
    KnowledgeService,
    SearchService,
    Settings,
    SkillService,
    VersionConflict,
)
from brain_db import Base, create_async_engine, create_async_session_factory
from brain_db.defaults import review_defaults, seed_defaults
from brain_db.seed import northstar_id, seed_northstar
from brain_schemas import (
    InvalidSkillDocument,
    PageCreate,
    PageVersionCreate,
    ProvenanceInput,
    SearchRequest,
    SkillCreate,
    SkillVersionCreate,
    SourceCreate,
)


class HttpClient(Protocol):
    def get(self, url: str, *, headers: dict[str, str] | None = None) -> Response: ...

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: object | None = None,
    ) -> Response: ...


@pytest.mark.integration
def test_postgres_has_vector_extension() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")

    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        row = cursor.fetchone()

    assert row is not None


@pytest.mark.integration
def test_clean_database_migration_and_tenant_constraints(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")

    sqlalchemy_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    monkeypatch.setenv("DATABASE_URL", sqlalchemy_url)
    config = Config("products/brain/alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    organization_a = uuid4()
    organization_b = uuid4()
    principal_a = uuid4()
    group_b = uuid4()
    policy_a = uuid4()
    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT version_num FROM alembic_version")
        assert cursor.fetchone() == ("20260913_0004",)
        cursor.execute(
            "INSERT INTO organizations (id, slug, name) "
            "VALUES (%s, 'alpha', 'Alpha'), (%s, 'beta', 'Beta')",
            (organization_a, organization_b),
        )
        cursor.execute(
            "INSERT INTO principals "
            "(id, organization_id, kind, external_subject, display_name) "
            "VALUES (%s, %s, 'user', 'alpha-user', 'Alpha User')",
            (principal_a, organization_a),
        )
        cursor.execute(
            "INSERT INTO groups (id, organization_id, slug, name) "
            "VALUES (%s, %s, 'beta-group', 'Beta Group')",
            (group_b, organization_b),
        )
        cursor.execute(
            "INSERT INTO access_policies (id, organization_id, name) VALUES (%s, %s, %s)",
            (policy_a, organization_a, "Alpha policy"),
        )
        with pytest.raises(ForeignKeyViolation):
            cursor.execute(
                "INSERT INTO group_memberships "
                "(organization_id, group_id, principal_id) VALUES (%s, %s, %s)",
                (organization_a, group_b, principal_a),
            )
        with pytest.raises(ForeignKeyViolation):
            cursor.execute(
                "INSERT INTO access_policy_groups "
                "(organization_id, access_policy_id, group_id) VALUES (%s, %s, %s)",
                (organization_a, policy_a, group_b),
            )
        with pytest.raises(CheckViolation):
            cursor.execute(
                "INSERT INTO principals "
                "(organization_id, kind, external_subject, display_name) "
                "VALUES (%s, 'administrator', 'invalid', 'Invalid')",
                (organization_a,),
            )
        cursor.execute("TRUNCATE organizations CASCADE")


@pytest.mark.integration
async def test_knowledge_services_constraints_and_seed() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    sqlalchemy_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    organization = uuid4()
    principal = uuid4()
    group = uuid4()
    open_policy = uuid4()
    restricted_policy = uuid4()
    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("TRUNCATE organizations CASCADE")
        cursor.execute(
            "INSERT INTO organizations (id, slug, name) VALUES (%s, 'test', 'Test')",
            (organization,),
        )
        cursor.execute(
            "INSERT INTO principals "
            "(id, organization_id, kind, external_subject, display_name) "
            "VALUES (%s, %s, 'user', 'tester', 'Tester')",
            (principal, organization),
        )
        cursor.execute(
            "INSERT INTO groups (id, organization_id, slug, name) "
            "VALUES (%s, %s, 'private', 'Private')",
            (group, organization),
        )
        cursor.execute(
            "INSERT INTO access_policies (id, organization_id, name) "
            "VALUES (%s, %s, 'Open'), (%s, %s, 'Restricted')",
            (open_policy, organization, restricted_policy, organization),
        )
        cursor.execute(
            "INSERT INTO access_policy_groups "
            "(organization_id, access_policy_id, group_id) VALUES (%s, %s, %s)",
            (organization, restricted_policy, group),
        )
        cursor.execute(
            "INSERT INTO group_memberships (organization_id, group_id, principal_id) "
            "VALUES (%s, %s, %s)",
            (organization, group, principal),
        )

    settings = Settings(database_url=PostgresDsn(sqlalchemy_url))
    engine = create_async_engine(settings)
    service = KnowledgeService(create_async_session_factory(engine))
    allowed = AuthContext(organization, principal, frozenset({group}))
    outsider = AuthContext(organization, principal, frozenset())
    source = await service.create_source(
        allowed,
        SourceCreate(
            source_type="memo",
            title="Memo",
            status="active",
            access_policy_id=restricted_policy,
            steward_id=principal,
        ),
    )
    page = await service.create_page(
        allowed,
        PageCreate(
            slug="policy",
            title="Policy",
            content_markdown="# Version one",
            access_policy_id=open_policy,
            steward_id=principal,
            sources=[ProvenanceInput(source_id=source.id, relationship="derived_from")],
        ),
    )
    updated = await service.create_page_version(
        allowed,
        page.id,
        PageVersionCreate(
            expected_current_version_id=page.current_version.id,
            content_markdown="# Version two",
            sources=[ProvenanceInput(source_id=source.id, relationship="corroborated_by")],
        ),
    )

    assert updated.current_version.version == 2
    assert [item.version for item in updated.versions] == [1, 2]
    with pytest.raises(DuplicatePageContent):
        await service.create_page_version(
            allowed,
            page.id,
            PageVersionCreate(
                expected_current_version_id=updated.current_version.id,
                content_markdown="# Version two",
            ),
        )
    assert (await service.get_page(outsider, page.id)).current_version.provenance == []
    with pytest.raises(AuthorizationDenied):
        await service.get_source(outsider, source.id)
    with pytest.raises(AuthorizationDenied):
        await service.get_page(AuthContext(uuid4(), principal, frozenset()), page.id)

    sync_engine = create_engine(sqlalchemy_url)
    with sync_engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(ProgrammingError):
            connection.execute(
                text("UPDATE page_versions SET content_markdown = '# changed' WHERE id = :id"),
                {"id": page.current_version.id},
            )
        transaction.rollback()

    second_page = await service.create_page(
        allowed,
        PageCreate(
            slug="second",
            title="Second",
            content_markdown="# Other Page",
            access_policy_id=open_policy,
            steward_id=principal,
        ),
    )
    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        with pytest.raises(ForeignKeyViolation):
            cursor.execute(
                "UPDATE pages SET current_version_id = %s WHERE id = %s",
                (page.current_version.id, second_page.id),
            )
        with pytest.raises(UniqueViolation):
            cursor.execute(
                "INSERT INTO sources "
                "(organization_id, source_type, title, external_id, status, "
                "access_policy_id, created_by_id, updated_by_id, steward_id) "
                "VALUES (%s, 'memo', 'Duplicate', 'duplicate', 'active', %s, %s, %s, %s), "
                "(%s, 'memo', 'Duplicate again', 'duplicate', 'active', %s, %s, %s, %s)",
                (
                    organization,
                    open_policy,
                    principal,
                    principal,
                    principal,
                    organization,
                    open_policy,
                    principal,
                    principal,
                    principal,
                ),
            )
        other_organization = uuid4()
        other_principal = uuid4()
        other_policy = uuid4()
        other_source = uuid4()
        cursor.execute(
            "INSERT INTO organizations (id, slug, name) VALUES (%s, 'other', 'Other')",
            (other_organization,),
        )
        cursor.execute(
            "INSERT INTO principals "
            "(id, organization_id, kind, external_subject, display_name) "
            "VALUES (%s, %s, 'user', 'other', 'Other')",
            (other_principal, other_organization),
        )
        cursor.execute(
            "INSERT INTO access_policies (id, organization_id, name) VALUES (%s, %s, 'Other')",
            (other_policy, other_organization),
        )
        cursor.execute(
            "INSERT INTO sources "
            "(id, organization_id, source_type, title, status, access_policy_id, "
            "created_by_id, updated_by_id, steward_id) "
            "VALUES (%s, %s, 'memo', 'Other source', 'active', %s, %s, %s, %s)",
            (
                other_source,
                other_organization,
                other_policy,
                other_principal,
                other_principal,
                other_principal,
            ),
        )
        with pytest.raises(ForeignKeyViolation):
            cursor.execute(
                "INSERT INTO page_version_sources "
                "(organization_id, page_version_id, source_id, relationship) "
                "VALUES (%s, %s, %s, 'derived_from')",
                (other_organization, page.current_version.id, other_source),
            )
    sync_engine.dispose()
    await engine.dispose()

    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("TRUNCATE organizations CASCADE")
    seed_northstar(sqlalchemy_url)
    seed_northstar(sqlalchemy_url)
    first_defaults = seed_defaults(
        sqlalchemy_url,
        organization_slug="northstar",
        policy_name="Northstar organization-wide",
        steward_external_subject="northstar-alex",
        audit_external_subject="northstar-cortex",
    )
    second_defaults = seed_defaults(
        sqlalchemy_url,
        organization_slug="northstar",
        policy_name="Northstar organization-wide",
        steward_external_subject="northstar-alex",
        audit_external_subject="northstar-cortex",
    )
    assert set(first_defaults.created) == {"index", "ingest", "retrieve", "update", "lint"}
    assert second_defaults.created == ()
    assert set(second_defaults.preserved) == {"index", "ingest", "retrieve", "update", "lint"}
    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT count(*) FROM pages")
        assert cursor.fetchone() == (4,)
        cursor.execute("SELECT count(*) FROM page_versions")
        assert cursor.fetchone() == (5,)
        cursor.execute("SELECT count(*) FROM skills")
        assert cursor.fetchone() == (5,)
        cursor.execute("SELECT count(*) FROM skill_versions")
        assert cursor.fetchone() == (5,)
        with pytest.raises(RaiseException):
            cursor.execute(
                "UPDATE folders SET deleted_at = now() WHERE id = %s",
                (northstar_id("folder:people"),),
            )


@pytest.mark.integration
async def test_skill_service_constraints_stale_writes_and_local_seed_divergence() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    sqlalchemy_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("TRUNCATE organizations CASCADE")
    seed_northstar(sqlalchemy_url)
    seed_defaults(
        sqlalchemy_url,
        organization_slug="northstar",
        policy_name="Northstar organization-wide",
        steward_external_subject="northstar-alex",
        audit_external_subject="northstar-cortex",
    )
    organization = northstar_id("organization:northstar")
    principal = northstar_id("principal:alex")
    policy = northstar_id("policy:organization-wide")
    context = AuthContext(organization, principal, frozenset())
    settings = Settings(database_url=PostgresDsn(sqlalchemy_url))
    engine = create_async_engine(settings)
    service = SkillService(create_async_session_factory(engine))
    markdown = """---
name: test
description: Test Skill.
inputs: {}
outputs: {}
tools: []
---

# Test
"""
    created = await service.create_skill(
        context,
        SkillCreate(
            slug="test-skill",
            name="Test Skill",
            content_markdown=markdown,
            access_policy_id=policy,
            steward_id=principal,
        ),
    )
    updated_markdown = markdown.replace("# Test", "# Test updated")
    updated = await service.create_skill_version(
        context,
        created.id,
        SkillVersionCreate(
            expected_current_version_id=created.current_version.id,
            content_markdown=updated_markdown,
        ),
    )
    with pytest.raises(VersionConflict):
        await service.create_skill_version(
            context,
            created.id,
            SkillVersionCreate(
                expected_current_version_id=created.current_version.id,
                content_markdown=markdown.replace("# Test", "# Stale"),
            ),
        )
    assert len((await service.get_skill(context, created.id)).versions) == 2
    with pytest.raises(InvalidSkillDocument):
        await service.create_skill_version(
            context,
            created.id,
            SkillVersionCreate(
                expected_current_version_id=updated.current_version.id,
                content_markdown="# invalid",
            ),
        )
    sync_engine = create_engine(sqlalchemy_url)
    with sync_engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(ProgrammingError):
            connection.execute(
                text("UPDATE skill_versions SET content_markdown = '# changed' WHERE id = :id"),
                {"id": created.current_version.id},
            )
        transaction.rollback()
    sync_engine.dispose()
    await engine.dispose()

    local_markdown = markdown.replace("name: test", "name: index").replace(
        "# Test", "# Locally edited index"
    )
    local_version_id = uuid4()
    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "SELECT id FROM skills WHERE organization_id = %s AND slug = 'index'", (organization,)
        )
        row = cast(tuple[UUID] | None, cursor.fetchone())
        assert row is not None
        index_skill_id = row[0]
        cursor.execute(
            "INSERT INTO skill_versions "
            "(id, organization_id, skill_id, version, content_markdown, content_hash, "
            "created_by_id) "
            "VALUES (%s, %s, %s, 2, %s, %s, %s)",
            (
                local_version_id,
                organization,
                index_skill_id,
                local_markdown,
                sha256(local_markdown.encode()).hexdigest(),
                principal,
            ),
        )
        cursor.execute(
            "UPDATE skills SET current_version_id = %s WHERE id = %s",
            (local_version_id, index_skill_id),
        )
    result = seed_defaults(
        sqlalchemy_url,
        organization_slug="northstar",
        policy_name="Northstar organization-wide",
        steward_external_subject="northstar-alex",
        audit_external_subject="northstar-cortex",
    )
    assert "index" in result.preserved
    review = {
        item.slug: item for item in review_defaults(sqlalchemy_url, organization_slug="northstar")
    }
    assert review["index"].status == "diverged"
    assert "Locally edited index" in review["index"].diff
    assert review["lint"].status == "current"
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT current_version_id FROM skills WHERE id = %s", (index_skill_id,))
        assert cursor.fetchone() == (local_version_id,)


@pytest.mark.integration
def test_alembic_has_no_model_metadata_drift() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    engine = create_engine(database_url.replace("postgresql://", "postgresql+psycopg://", 1))
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert differences == []


@pytest.mark.integration
async def test_search_filters_candidates_before_ranking_and_current_version_limit() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    sqlalchemy_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("TRUNCATE organizations CASCADE")
    seed_northstar(sqlalchemy_url)

    settings = Settings(database_url=PostgresDsn(sqlalchemy_url))
    engine = create_async_engine(settings)
    search = SearchService(create_async_session_factory(engine))
    organization = northstar_id("organization:northstar")
    principal = northstar_id("principal:alex")
    group = northstar_id("group:investment")
    project = northstar_id("page:project-orion")
    current_version = northstar_id("page:project-orion:version:2")
    other_organization = northstar_id("organization:harbour")
    other_principal = northstar_id("principal:harbour")
    other_policy, other_page, other_version, other_chunk = (uuid4() for _ in range(4))
    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "INSERT INTO access_policies "
            "(id, organization_id, name) VALUES (%s, %s, 'Harbour open')",
            (other_policy, other_organization),
        )
        cursor.execute(
            "INSERT INTO pages (id, organization_id, slug, title, access_policy_id, "
            "position, steward_id, created_by_id, updated_by_id) "
            "VALUES (%s, %s, 'cross-tenant', 'Cross tenant secret', %s, 0, %s, %s, %s)",
            (
                other_page,
                other_organization,
                other_policy,
                other_principal,
                other_principal,
                other_principal,
            ),
        )
        cursor.execute(
            "INSERT INTO page_versions "
            "(id, organization_id, page_id, version, content_markdown, content_hash, "
            "created_by_id) "
            "VALUES (%s, %s, %s, 1, '# Orion revenue cross-tenant classified', %s, %s)",
            (
                other_version,
                other_organization,
                other_page,
                sha256(b"# Orion revenue cross-tenant classified").hexdigest(),
                other_principal,
            ),
        )
        cursor.execute(
            "UPDATE pages SET current_version_id = %s WHERE id = %s",
            (other_version, other_page),
        )
        cursor.execute(
            "INSERT INTO chunks (id, organization_id, page_version_id, position, heading_path, "
            "content, content_hash, embedding) "
            "VALUES (%s, %s, %s, 0, '[]', 'Orion revenue cross-tenant classified', %s, "
            "'[1,0,0,0,0,0,0,0]')",
            (
                other_chunk,
                other_organization,
                other_version,
                sha256(b"Orion revenue cross-tenant classified").hexdigest(),
            ),
        )

    allowed = await search.search(
        AuthContext(organization, principal, frozenset({group})),
        SearchRequest(query="Orion revenue", limit=10),
    )
    outsider = await search.search(
        AuthContext(organization, principal, frozenset()),
        SearchRequest(query="Orion revenue", limit=1),
    )
    repeated = await search.search(
        AuthContext(organization, principal, frozenset({group})),
        SearchRequest(query="Orion revenue", limit=10),
    )
    semantic_only = await search.search(
        AuthContext(organization, principal, frozenset({group})),
        SearchRequest(query="unfindabletoken", limit=2),
    )

    project_results = [result for result in allowed.results if result.page_id == project]
    assert project_results
    assert any(result.lexical_score > 0 for result in project_results)
    assert all(
        abs(result.score - result.lexical_score - result.semantic_score) < 1e-6
        for result in allowed.results
    )
    assert [(result.chunk_id, result.score) for result in repeated.results] == [
        (result.chunk_id, result.score) for result in allowed.results
    ]
    assert semantic_only.results
    assert all(result.lexical_score == 0 for result in semantic_only.results)
    assert all(result.page_version_id == current_version for result in project_results)
    assert outsider.results
    assert all(result.page_id != project for result in outsider.results)
    assert all(result.page_id != other_page for result in allowed.results + outsider.results)
    assert all("£45m" not in result.snippet for result in outsider.results)
    await engine.dispose()


@pytest.mark.integration
async def test_http_and_mcp_have_equivalent_knowledge_access() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    sqlalchemy_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("TRUNCATE organizations CASCADE")
    seed_northstar(sqlalchemy_url)

    organization = northstar_id("organization:northstar")
    principal = northstar_id("principal:alex")
    group = northstar_id("group:investment")
    open_policy = northstar_id("policy:organization-wide")
    restricted_policy = northstar_id("policy:deal-team")
    restricted_source = northstar_id("source:committee-notes")
    settings = Settings(database_url=PostgresDsn(sqlalchemy_url))
    service = KnowledgeService(create_async_session_factory(create_async_engine(settings)))
    skill_service = SkillService(create_async_session_factory(create_async_engine(settings)))
    search_service = SearchService(create_async_session_factory(create_async_engine(settings)))
    allowed_context = AuthContext(organization, principal, frozenset({group}))
    page = await service.create_page(
        allowed_context,
        PageCreate(
            slug="transport-parity",
            title="Transport parity",
            content_markdown="# Transport parity",
            access_policy_id=open_policy,
            steward_id=principal,
            sources=[ProvenanceInput(source_id=restricted_source, relationship="derived_from")],
        ),
    )
    skill_markdown = """---
name: transport-skill
description: Transport parity Skill.
inputs: {}
outputs: {}
tools:
  - list_pages
---

# Transport Skill
"""
    skill = await skill_service.create_skill(
        allowed_context,
        SkillCreate(
            slug="transport-skill",
            name="Transport Skill",
            content_markdown=skill_markdown,
            access_policy_id=open_policy,
            steward_id=principal,
        ),
    )
    restricted_skill = await skill_service.create_skill(
        allowed_context,
        SkillCreate(
            slug="restricted-skill",
            name="Restricted Skill",
            content_markdown=skill_markdown.replace("transport-skill", "restricted-skill"),
            access_policy_id=restricted_policy,
            steward_id=principal,
        ),
    )

    async def mcp_result(context: AuthContext, tool: str, arguments: dict[str, object]):
        app = create_app(
            knowledge_service=service,
            skill_service=skill_service,
            search_service=search_service,
            authenticator=LocalBearerAuthenticator(token="secret", context=context),
        )

        def client_factory(
            headers: dict[str, str] | None = None,
            timeout: httpx.Timeout | None = None,
            auth: httpx.Auth | None = None,
            **kwargs: object,
        ) -> httpx.AsyncClient:
            return httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
                headers=headers,
                timeout=timeout,
                auth=auth,
            )

        transport = StreamableHttpTransport(
            "http://testserver/mcp/",
            headers={"Authorization": "Bearer secret"},
            httpx_client_factory=client_factory,
        )
        async with app.router.lifespan_context(app), Client(transport) as client:
            return await client.call_tool(tool, arguments, raise_on_error=False)

    allowed_app = create_app(
        knowledge_service=service,
        skill_service=skill_service,
        search_service=search_service,
        authenticator=LocalBearerAuthenticator(token="secret", context=allowed_context),
    )
    allowed_client = cast(HttpClient, TestClient(allowed_app))
    allowed_http = allowed_client.get(
        f"/pages/{page.id}", headers={"Authorization": "Bearer secret"}
    )
    allowed_mcp = await mcp_result(allowed_context, "get_page", {"page_id": str(page.id)})
    created_http = allowed_client.post(
        "/pages",
        headers={"Authorization": "Bearer secret"},
        json={
            "slug": "http-created",
            "title": "HTTP created",
            "content_markdown": "# HTTP created",
            "access_policy_id": str(open_policy),
            "steward_id": str(principal),
        },
    )
    created_mcp = await mcp_result(
        allowed_context,
        "create_page",
        {
            "request": {
                "slug": "mcp-created",
                "title": "MCP created",
                "content_markdown": "# MCP created",
                "access_policy_id": str(open_policy),
                "steward_id": str(principal),
            }
        },
    )
    assert allowed_http.status_code == 200
    assert allowed_mcp.is_error is False
    assert created_http.status_code == 201
    assert created_mcp.is_error is False
    assert isinstance(allowed_mcp.structured_content, dict)
    assert len(allowed_http.json()["current_version"]["provenance"]) == 1
    assert len(allowed_mcp.structured_content["current_version"]["provenance"]) == 1
    search_http = allowed_client.post(
        "/search",
        headers={"Authorization": "Bearer secret"},
        json={"query": "Transport parity", "limit": 5},
    )
    search_mcp = await mcp_result(
        allowed_context,
        "search",
        {"request": {"query": "Transport parity", "limit": 5}},
    )
    assert search_http.status_code == 200
    assert search_mcp.is_error is False
    assert search_mcp.structured_content == search_http.json()
    skill_http = allowed_client.get(
        "/skills/by-slug/transport-skill", headers={"Authorization": "Bearer secret"}
    )
    skill_mcp = await mcp_result(allowed_context, "get_skill_by_slug", {"slug": "transport-skill"})
    assert skill_http.status_code == 200
    assert skill_mcp.is_error is False
    assert skill_http.json()["current_version"]["content_markdown"] == skill_markdown
    assert isinstance(skill_mcp.structured_content, dict)
    assert skill_mcp.structured_content["current_version"]["content_markdown"] == skill_markdown

    stale_request = {
        "expected_current_version_id": str(uuid4()),
        "content_markdown": skill_markdown.replace("# Transport Skill", "# Stale"),
    }
    conflict_http = allowed_client.post(
        f"/skills/{skill.id}/versions",
        headers={"Authorization": "Bearer secret"},
        json=stale_request,
    )
    conflict_mcp = await mcp_result(
        allowed_context,
        "create_skill_version",
        {"skill_id": str(skill.id), "request": stale_request},
    )
    assert conflict_http.status_code == 409
    assert conflict_mcp.is_error is True

    outsider = AuthContext(organization, principal, frozenset())
    outsider_app = create_app(
        knowledge_service=service,
        skill_service=skill_service,
        search_service=search_service,
        authenticator=LocalBearerAuthenticator(token="secret", context=outsider),
    )
    outsider_client = cast(HttpClient, TestClient(outsider_app))
    denied_http = outsider_client.get(
        f"/sources/{restricted_source}", headers={"Authorization": "Bearer secret"}
    )
    denied_mcp = await mcp_result(outsider, "get_source", {"source_id": str(restricted_source)})
    hidden_http = outsider_client.get(
        f"/pages/{page.id}", headers={"Authorization": "Bearer secret"}
    )
    hidden_mcp = await mcp_result(outsider, "get_page", {"page_id": str(page.id)})
    missing_id = uuid4()
    missing_http = outsider_client.get(
        f"/pages/{missing_id}", headers={"Authorization": "Bearer secret"}
    )
    missing_mcp = await mcp_result(outsider, "get_page", {"page_id": str(missing_id)})
    denied_skill_http = outsider_client.get(
        f"/skills/{restricted_skill.id}", headers={"Authorization": "Bearer secret"}
    )
    denied_skill_mcp = await mcp_result(
        outsider, "get_skill", {"skill_id": str(restricted_skill.id)}
    )
    missing_skill_http = outsider_client.get(
        f"/skills/{missing_id}", headers={"Authorization": "Bearer secret"}
    )
    missing_skill_mcp = await mcp_result(outsider, "get_skill", {"skill_id": str(missing_id)})
    assert denied_http.status_code == 403
    assert denied_mcp.is_error is True
    assert hidden_http.json()["current_version"]["provenance"] == []
    assert isinstance(hidden_mcp.structured_content, dict)
    assert hidden_mcp.structured_content["current_version"]["provenance"] == []
    assert missing_http.status_code == 404
    assert missing_mcp.is_error is True
    assert denied_skill_http.status_code == 403
    assert denied_skill_mcp.is_error is True
    assert missing_skill_http.status_code == 404
    assert missing_skill_mcp.is_error is True


@pytest.mark.integration
async def test_concurrent_page_and_skill_writers_publish_one_winner() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    sqlalchemy_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("TRUNCATE organizations CASCADE")
    seed_northstar(sqlalchemy_url)

    settings = Settings(database_url=PostgresDsn(sqlalchemy_url), database_pool_size=2)
    engine = create_async_engine(settings)
    factory = create_async_session_factory(engine)
    knowledge = KnowledgeService(factory)
    skills = SkillService(factory)
    organization = northstar_id("organization:northstar")
    principal = northstar_id("principal:alex")
    policy = northstar_id("policy:organization-wide")
    context = AuthContext(organization, principal, frozenset())
    page = await knowledge.create_page(
        context,
        PageCreate(
            slug="concurrent-page",
            title="Concurrent Page",
            content_markdown="# Base",
            access_policy_id=policy,
            steward_id=principal,
        ),
    )
    skill_document = """---
name: concurrent-skill
description: Concurrency test.
inputs: {}
outputs: {}
tools: []
---

# Base
"""
    skill = await skills.create_skill(
        context,
        SkillCreate(
            slug="concurrent-skill",
            name="Concurrent Skill",
            content_markdown=skill_document,
            access_policy_id=policy,
            steward_id=principal,
        ),
    )

    page_results = await asyncio.gather(
        *(
            knowledge.create_page_version(
                context,
                page.id,
                PageVersionCreate(
                    expected_current_version_id=page.current_version.id,
                    content_markdown=f"# Writer {writer}",
                ),
            )
            for writer in ("A", "B")
        ),
        return_exceptions=True,
    )
    skill_results = await asyncio.gather(
        *(
            skills.create_skill_version(
                context,
                skill.id,
                SkillVersionCreate(
                    expected_current_version_id=skill.current_version.id,
                    content_markdown=skill_document.replace("# Base", f"# Writer {writer}"),
                ),
            )
            for writer in ("A", "B")
        ),
        return_exceptions=True,
    )

    for results in (page_results, skill_results):
        assert sum(isinstance(result, VersionConflict) for result in results) == 1
        assert sum(not isinstance(result, BaseException) for result in results) == 1
    assert len((await knowledge.get_page(context, page.id)).versions) == 2
    assert len((await skills.get_skill(context, skill.id)).versions) == 2
    await engine.dispose()


@pytest.mark.integration
async def test_small_async_pool_waits_responsively_and_times_out_cleanly() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    sqlalchemy_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    settings = Settings(
        database_url=PostgresDsn(sqlalchemy_url),
        database_pool_size=2,
        database_max_overflow=0,
        database_pool_timeout_seconds=0.05,
        database_statement_timeout_ms=50,
    )
    engine = create_async_engine(settings)
    factory = create_async_session_factory(engine)

    first = factory()
    second = factory()
    await first.execute(text("SELECT 1"))
    await second.execute(text("SELECT 1"))
    waiting = factory()
    with pytest.raises(SQLAlchemyTimeoutError):
        await waiting.execute(text("SELECT 1"))
    await waiting.close()
    await second.close()

    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        for _ in range(5):
            await asyncio.sleep(0.01)
            if ticks == 0:
                assert not statement.done()
            ticks += 1

    started = perf_counter()
    statement = asyncio.create_task(first.execute(text("SELECT pg_sleep(0.2)")))
    await ticker()
    with pytest.raises(DBAPIError):
        await statement
    assert ticks == 5
    assert perf_counter() - started < 0.5
    await first.rollback()
    await first.close()
    await engine.dispose()


@pytest.mark.integration
async def test_hundred_concurrent_http_and_mcp_reads_share_a_small_pool() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    sqlalchemy_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    with (
        psycopg.connect(database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("TRUNCATE organizations CASCADE")
    seed_northstar(sqlalchemy_url)
    seed_defaults(
        sqlalchemy_url,
        organization_slug="northstar",
        policy_name="Northstar organization-wide",
        steward_external_subject="northstar-alex",
        audit_external_subject="northstar-cortex",
    )

    settings = Settings(
        database_url=PostgresDsn(sqlalchemy_url),
        database_pool_size=5,
        database_max_overflow=0,
        database_pool_timeout_seconds=5,
    )
    engine = create_async_engine(settings)
    factory = create_async_session_factory(engine)
    knowledge = KnowledgeService(factory)
    skills = SkillService(factory)
    organization = northstar_id("organization:northstar")
    principal = northstar_id("principal:alex")
    group = northstar_id("group:investment")
    restricted_source = northstar_id("source:committee-notes")
    allowed = AuthContext(organization, principal, frozenset({group}))
    outsider = AuthContext(organization, principal, frozenset())

    def app_for(context: AuthContext) -> FastAPI:
        return create_app(
            settings=settings,
            knowledge_service=knowledge,
            skill_service=skills,
            authenticator=LocalBearerAuthenticator(token="secret", context=context),
        )

    allowed_app = app_for(allowed)
    denied_app = app_for(outsider)
    headers = {"Authorization": "Bearer secret"}
    allowed_http = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=allowed_app),
        base_url="http://testserver",
        headers=headers,
    )
    denied_http = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=denied_app),
        base_url="http://testserver",
        headers=headers,
    )

    def mcp_transport(app: FastAPI) -> StreamableHttpTransport:
        def client_factory(
            headers: dict[str, str] | None = None,
            timeout: httpx.Timeout | None = None,
            auth: httpx.Auth | None = None,
            **kwargs: object,
        ) -> httpx.AsyncClient:
            return httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
                headers=headers,
                timeout=timeout,
                auth=auth,
            )

        return StreamableHttpTransport(
            "http://testserver/mcp/",
            headers={"Authorization": "Bearer secret"},
            httpx_client_factory=client_factory,
        )

    allowed_mcp = Client(mcp_transport(allowed_app))
    denied_mcp = Client(mcp_transport(denied_app))

    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        for _ in range(10):
            await asyncio.sleep(0)
            ticks += 1

    async def timed[T](operation: Awaitable[T]) -> tuple[T, float]:
        request_started = perf_counter()
        result = await operation
        return result, perf_counter() - request_started

    async with (
        allowed_app.router.lifespan_context(allowed_app),
        denied_app.router.lifespan_context(denied_app),
        allowed_http,
        denied_http,
        allowed_mcp,
        denied_mcp,
    ):
        http_calls = [
            allowed_http.get(("/pages", "/sources", "/skills")[index % 3]) for index in range(40)
        ] + [denied_http.get(f"/sources/{restricted_source}") for _ in range(10)]
        mcp_calls = [
            allowed_mcp.call_tool(("list_pages", "list_sources", "list_skills")[index % 3])
            for index in range(40)
        ] + [
            denied_mcp.call_tool(
                "get_source", {"source_id": str(restricted_source)}, raise_on_error=False
            )
            for _ in range(10)
        ]
        started = perf_counter()
        gathered = await asyncio.wait_for(
            asyncio.gather(
                *(timed(operation) for operation in http_calls),
                *(timed(operation) for operation in mcp_calls),
                ticker(),
            ),
            timeout=30,
        )
        elapsed = perf_counter() - started

    timed_results = cast(list[tuple[object, float]], gathered[:100])
    http_results = cast(list[Response], [result for result, _ in timed_results[:50]])
    mcp_results = cast(list[CallToolResult], [result for result, _ in timed_results[50:]])
    latencies = sorted(duration for _, duration in timed_results)
    print(
        "async-load "
        f"requests=100 pool=5 overflow=0 elapsed={elapsed:.3f}s "
        f"throughput={100 / elapsed:.1f}rps "
        f"p50={latencies[49] * 1000:.1f}ms p95={latencies[94] * 1000:.1f}ms"
    )
    assert all(response.status_code == 200 for response in http_results[:40])
    assert all(response.status_code == 403 for response in http_results[40:])
    assert all(not result.is_error for result in mcp_results[:40])
    assert all(result.is_error for result in mcp_results[40:])
    assert ticks == 10
    assert "Checked out connections: 0" in engine.pool.status()
    await engine.dispose()
