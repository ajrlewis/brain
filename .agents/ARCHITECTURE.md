# Architecture

`README.md` is the canonical target-state specification. The implemented foundation is a Python 3.13 uv workspace with HTTP and MCP health interfaces over a shared application service. Domain behavior and persistence remain target state unless explicitly identified below.

## Purpose And Boundary

Brain is a self-hosted, agent-agnostic store for governed organisational knowledge and reusable agent Skills. It stores and serves durable state through HTTP and MCP. It does not browse, fetch provider content, execute Skills, select tools, or orchestrate agent workflows; Cortex or another external agent owns those responsibilities.

## Components And Dependency Direction

```text
HTTP API ─┐
          ├─> shared domain/application services ─> persistence/search ─> PostgreSQL + pgvector
MCP ──────┘                                  └─────> provider-neutral embeddings
```

- `apps/api` and `apps/mcp` are thin transport boundaries over shared services.
- `packages/core` currently owns typed settings and the shared health application service; it will own domain behavior and invariants.
- `packages/schemas` currently owns the transport-neutral health response contract.
- `packages/db`, `packages/ai`, `packages/search`, and `packages/auth` establish installable dependency boundaries only. Their domain APIs are intentionally deferred.
- `packages/db` declares the SQLAlchemy, psycopg, and pgvector client dependencies. No database models or Alembic migrations exist because this milestone adds no schema.

Applications may depend on packages; packages must not depend on applications. HTTP and MCP must not independently implement domain rules.

Both implemented interfaces accept an injected `HealthService`. FastAPI exposes `GET /health`
and mounts FastMCP's Streamable HTTP transport at `/mcp/` in the same ASGI application;
FastMCP exposes the `health` tool. The separate `brain-mcp` command preserves the stdio
transport for local clients. Neither health check performs database work.

## Durable Data Rules

- `Source` records provenance; `Page` records stable knowledge identity; immutable `PageVersion` records content.
- Provenance attaches to the version produced from a source through `PageVersionSource`.
- `Skill` is the only capability primitive. Immutable `SkillVersion` documents contain YAML frontmatter plus Markdown instructions.
- Parent entities point to their current version; version content and hashes are not duplicated onto parents.
- Chunks and embeddings are derived, attributable, and safe to regenerate without changing canonical content.
- Folders provide typed hierarchy; tags provide classification and never authorization.
- Top-level domain data is organization-scoped.

## Security And Retrieval Invariants

Authorization must constrain retrieval candidates before ranking or result limiting. Unauthorized titles, snippets, semantic matches, chunks, provenance, and other metadata must never be returned. HTTP and MCP enforce identical authorization and domain rules.

Use a provider-neutral `AuthContext` containing organization, principal, and group identities. Access policies are organization-wide when unrestricted; when groups are configured, membership in at least one permitted group is required.

## Runtime And External Boundaries

The implemented stack is Python 3.13+, uv, FastAPI, FastMCP, Pydantic v2, SQLAlchemy 2.x, psycopg, pgvector, PostgreSQL 17 with pgvector, pytest, Ruff, Pyright, Docker, and GitHub Actions. Alembic will be added with the first schema change.

The service should remain containerizable and host-independent even though production is intended for Vercel with managed PostgreSQL. Repository code and migrations are canonical; hosted systems are authoritative only for live deployment and database state. Deployment, production data access or mutation, hosted configuration changes, and secret changes require explicit maintainer authorization.

Structured logs should carry correlation IDs across HTTP/MCP, database, search, and embedding-provider boundaries without recording secrets, sensitive content, or hidden model reasoning.
