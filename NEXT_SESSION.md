# Next Session

## Objective

Build the first governed knowledge vertical slice on the completed identity,
access-control, Alembic, and Compose foundation. Persist deterministic Northstar example
knowledge and expose the same create/read behavior through HTTP and MCP application
services.

Preserve the implemented boundary:

```text
HTTP ─┐
      ├── shared application services(AuthContext, ...) ──> repositories ──> PostgreSQL
MCP ──┘
```

Database models are persistence details, not public HTTP, MCP, or domain contracts.

## Immediate Scope

### 1. Knowledge persistence

Implement the already specified contracts in `docs/DATA_MODEL.md` for:

- Folder (`page` kind only in this slice);
- Source;
- Page and immutable PageVersion;
- PageVersionSource;
- valid same-Page current-version pointers and same-Organization references.

Add a new Alembic revision rather than changing the applied identity/access revision.
Keep Markdown only on PageVersion. Do not add chunks, embeddings, tags, Skills, or a
generic Asset entity yet.

### 2. Shared services and repositories

Add minimal create/read application services and explicit public schemas. Services must
accept `AuthContext`, invoke `brain_auth.require_access`, and own all versioning,
same-tenant, provenance, and authorization rules. Repositories participate in a
caller-owned session/unit of work.

Page access controls its title, content, and versions. Source access independently
controls direct retrieval. Provenance output is the intersection of Page and Source
access and must not reveal hidden Source identifiers or counts.

### 3. HTTP and MCP parity

Expose focused create/read operations through thin FastAPI routes and FastMCP tools over
the same services. Test equivalent allow and deny behavior, including restricted groups,
wrong-Organization access, missing records, immutable version creation, and hidden
provenance. Keep both health interfaces database-free and unauthenticated.

### 4. Deterministic Northstar seed

Add an explicit, repeatable seed command for a wholly fictional Northstar private-equity
firm. Include Organizations, Principals, Groups, policies, folders, Sources, Pages,
versions, and provenance. Represent people, teams, and positions as ordinary Pages. Seed
overlapping or superseded facts to demonstrate provenance and versioning. It must be safe
to rerun without duplicating records.

Use synthetic text fixtures only. Binary PDFs and brand assets may be added as fixtures,
but binary delivery remains deferred.

## Definition of Done

- The new migration upgrades a clean PostgreSQL database and Alembic reports no metadata
  drift.
- PostgreSQL integration tests prove current-version, tenant, uniqueness, provenance, and
  immutability constraints.
- HTTP and mounted MCP create/read operations share services and have equivalent allow and
  deny behavior.
- The explicit Northstar seed is deterministic and idempotent.
- Existing health checks and the postgres → migrate → api Compose lifecycle still pass.
- Ruff, formatting, Pyright, unit/E2E tests, integration tests, Compose configuration, and
  the Docker image build pass.
- README and agent context describe only behavior actually implemented.

## Explicitly Deferred

- Skill and SkillVersion persistence;
- chunks, full-text/vector search, embeddings, and external AI providers;
- document parsing or agent-driven ingestion;
- binary asset delivery over MCP;
- production identity-provider integration;
- the Next.js web console, deployment, and production configuration.
