# Architecture

`README.md` is the canonical target-state specification. At present, the repository has no implemented application; everything below describes durable intended boundaries, not existing components.

## Purpose And Boundary

Brain is a self-hosted, agent-agnostic store for governed organisational knowledge and reusable agent Skills. It stores and serves durable state through HTTP and MCP. It does not browse, fetch provider content, execute Skills, select tools, or orchestrate agent workflows; Cortex or another external agent owns those responsibilities.

## Intended Components

```text
HTTP API ─┐
          ├─> shared domain/application services ─> persistence/search ─> PostgreSQL + pgvector
MCP ──────┘                                  └─────> provider-neutral embeddings
```

- `apps/api` and `apps/mcp` are thin transport boundaries over shared services.
- `packages/core` owns domain behavior and invariants.
- `packages/db` owns SQLAlchemy persistence, PostgreSQL behavior, and Alembic integration.
- `packages/ai` isolates embedding-provider implementations; it is not a Skill runtime.
- `packages/search` owns retrieval, ranking, provenance shaping, and authorization filtering.
- `packages/auth` produces a consistent authorization context, separate from authentication mechanisms.
- `packages/schemas` holds explicit shared public contracts where useful.

Applications may depend on packages; packages must not depend on applications. HTTP and MCP must not independently implement domain rules.

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

The intended stack is Python 3.13+, uv, FastAPI, FastMCP, Pydantic v2, SQLAlchemy 2.x, Alembic, PostgreSQL with pgvector, pytest, Ruff, Pyright, Docker, and GitHub Actions.

The service should remain containerizable and host-independent even though production is intended for Vercel with managed PostgreSQL. Repository code and migrations are canonical; hosted systems are authoritative only for live deployment and database state. Deployment, production data access or mutation, hosted configuration changes, and secret changes require explicit maintainer authorization.

Structured logs should carry correlation IDs across HTTP/MCP, database, search, and embedding-provider boundaries without recording secrets, sensitive content, or hidden model reasoning.
