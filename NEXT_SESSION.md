# Next Session

## Objective

Implement Brain's first authorization-safe hybrid search slice across PostgreSQL, the shared
application service, HTTP/MCP transports, and the read-only web console.

Complete PR #13 and confirm its Compose/Playwright checks are green before starting this slice.

## Scope

### 1. Derived retrieval data

- Add immutable-version-attributed `Chunk` persistence and an Alembic migration. Chunks inherit
  authorization exclusively through their Page and current PageVersion.
- Define deterministic Markdown chunking with stable ordering, heading paths, content hashes,
  and explicit regeneration behavior. Do not make chunks canonical or independently editable.
- Add a provider-neutral embedding interface. Tests and local development must use a
  deterministic synthetic implementation and must not require an external AI provider.

### 2. Authorization-safe hybrid search

- Implement PostgreSQL full-text and pgvector candidate retrieval behind `packages/search`.
- Constrain candidates by organization and access policy before ranking or limiting. Restricted
  titles, paths, snippets, scores, chunks, and provenance must never be observable.
- Combine lexical and semantic candidates with a small deterministic ranking contract. Keep
  pgvector and PostgreSQL details behind the search package boundary.
- Expose bounded, typed search requests and results through one shared application service.

### 3. HTTP, MCP, and web console

- Add equivalent thin HTTP and MCP search interfaces over the shared service.
- Regenerate the FastAPI OpenAPI document and web Zod schemas; the drift check must remain green.
- Add a responsive search experience to the enterprise console with query, loading, empty,
  denied, invalid, and backend-failure states. Results must show Page identity, a safe snippet,
  and enough provenance to inspect the source Page without exposing inaccessible metadata.
- Keep bearer credentials server-only and preserve the existing three-pane console boundary.

### 4. Verification and documentation

- Test deterministic chunk generation and regeneration, lexical/semantic/hybrid ranking,
  malformed embeddings, empty queries, bounded limits, and stale/current PageVersion behavior.
- Add PostgreSQL integration tests proving unauthorized content cannot enter candidates before
  ranking or result limiting, including same-tenant group restrictions and cross-tenant data.
- Add HTTP/MCP parity tests and a Playwright Northstar search flow.
- Run Python and TypeScript lint, formatting, type checks, unit/component tests, PostgreSQL
  integration tests, contract drift checks, production builds, Compose health, and browser tests.
- Update README, architecture, data model, access-control semantics, commands, and agent context.

## Definition Of Done

- Authorized users receive useful, deterministic hybrid results over current PageVersions.
- Unauthorized content is excluded in the database candidate query and cannot affect result
  counts, ranks, snippets, timing assertions used by tests, or provenance.
- HTTP, MCP, and web consumers share explicit generated contracts and equivalent domain rules.
- Chunk and embedding data can be regenerated without changing canonical Pages or provenance.
- All documented Python, TypeScript, PostgreSQL, Docker, Compose, and browser checks pass.

## Explicitly Deferred

- Production embedding-provider selection, credentials, quotas, and hosted deployment;
- rerankers, query rewriting, personalization, analytics, and relevance-learning pipelines;
- Page or Skill editing, access-policy administration, and organization branding management;
- binary document ingestion, provider connectors, and background orchestration.
