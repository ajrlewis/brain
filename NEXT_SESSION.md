# Next Session

## Objective

Establish Brain's first persistent, authorization-aware foundation so a clean checkout can
start PostgreSQL, apply real Alembic migrations, run the combined FastAPI/FastMCP service,
and load deterministic Northstar example data.

The next session should preserve the current boundary:

```text
HTTP ─┐
      ├── shared application services(AuthContext, ...) ──> repositories ──> PostgreSQL
MCP ──┘
```

FastAPI and FastMCP are interfaces over the same services. Database models must not become
the public HTTP, MCP, or domain contract.

## Immediate Scope

### 1. Define the contracts before the schema

Create:

- `docs/DATA_MODEL.md`
- `docs/ACCESS_CONTROL.md`

`DATA_MODEL.md` should define fields, identifiers, constraints, relationships, deletion
behavior, current-version pointers, and organization scoping for the initial model. Cover
at least:

- Organization, Principal, Group, GroupMembership, AccessPolicy, and AccessPolicyGroup
- Folder
- Source
- Page, PageVersion, and PageVersionSource
- Skill and SkillVersion
- the boundary between canonical content and derived chunks/embeddings

Keep Markdown content only on immutable `PageVersion` and `SkillVersion` records. A `Page`
or `Skill` provides stable identity and points to its current version.

`ACCESS_CONTROL.md` should make these initial semantics executable:

- every top-level record is organization-scoped;
- no permitted groups means organization-wide access;
- one or more permitted groups means membership in at least one group is required;
- a Page's policy controls its versions, chunks, search results, titles, and snippets;
- a Source's policy controls direct Source retrieval;
- provenance must not reveal a Source the caller cannot access;
- authorization constrains retrieval candidates before ranking or limiting.

Do not add role hierarchies, SCIM, SAML administration, or provider-specific identity
models in this slice.

### 2. Add the persistence and migration foundation

Implement in `packages/db`:

- SQLAlchemy declarative metadata and naming conventions;
- typed engine and session factories based on `Settings.database_url`;
- repository/session boundaries suitable for dependency injection;
- Alembic configuration rooted in the repository;
- an initial migration for the agreed identity and access-control foundation.

Add focused PostgreSQL integration tests that apply migrations to a clean database and
verify important constraints. Do not substitute SQLite for PostgreSQL-specific behavior.

### 3. Complete the Compose lifecycle

Add a one-shot `migrate` service using the application image:

```text
postgres --healthy--> migrate --completed--> api
```

The API must not run migrations implicitly during process startup. Document and verify:

- starting PostgreSQL;
- applying migrations explicitly;
- starting the API after migration success;
- running integration tests against the Compose database;
- resetting the disposable database volume, with a clear data-loss warning.

### 4. Introduce the shared authorization context

Implement the provider-neutral shape in `packages/auth`:

```text
AuthContext
├── organization_id
├── principal_id
└── group_ids
```

Use one deliberately simple bearer-token authenticator for local development. The parent
ASGI layer may authenticate both HTTP and mounted MCP traffic, but each transport needs a
thin adapter that retrieves the shared context. Domain services must accept `AuthContext`
and enforce authorization themselves.

Prove equivalent allow and deny behavior through HTTP and MCP. Keep the health endpoint
usable for container health checks without database-backed authentication.

## Subsequent Vertical Slices

Implement these as focused follow-up changes rather than one large schema-and-product PR.

### Knowledge and seed data

- Add Folder, Source, Page, PageVersion, and PageVersionSource persistence and services.
- Add create/read operations through both HTTP and MCP.
- Enforce Page policy over Markdown content and every Page-derived representation.
- Load deterministic seed data for the fictional Northstar private-equity firm.
- Represent its team and positions as ordinary knowledge Pages initially, not as a new HR
  domain model.
- Include synthetic PDFs and brand assets under `examples/northstar/`; never use real
  confidential company material.

The seed should contain overlapping or superseded facts so provenance and versioning can
be demonstrated. Seed loading must be explicit, repeatable, and safe to rerun.

### Initial Cortex-facing Skills

Store initial example Skills as versioned Markdown with YAML frontmatter:

- `ingest`: turn supplied source material into governed Sources, Pages, and versions;
- `search`: choose and call authorized knowledge search;
- `retrieve`: navigate folders and retrieve Pages, Sources, or Skills;
- `update`: create new immutable versions instead of overwriting content;
- `index`: explain routing, derived-index rebuilding, and governance checks;
- `brand`: expose visual-identity guidance, palette, layouts, and referenced brand assets;
- `voice`: expose writing style, terminology, and tone guidance.

These Skills instruct Cortex or another agent how to act. Brain stores, validates, and
serves them; Brain does not execute the procedures.

Avoid duplicating MCP tool definitions inside Skill documents. A Skill may explain when
and how to call stable MCP tools such as `search`, `get_page`, or `create_page_version`.

### Search and indexing

- Add canonical chunk derivation from PageVersion content.
- Add provider-neutral embeddings with recorded provider, model, and dimensions.
- Search Source metadata and authorized Page chunks.
- Apply authorization in the database candidate query before ranking and result limits.
- Make indexes and embeddings disposable and rebuildable from canonical versions.

### Brand assets

Create a polished but entirely fictional Northstar logo and example document layouts.
Treat each binary fixture as a Source with provenance. Before implementing delivery,
choose and document whether MCP returns an HTTP asset URL or exposes the file as an MCP
resource; do not introduce a generic Asset entity without a demonstrated need.

### Web console

After the HTTP contracts stabilize, add `apps/web` as a Next.js management and inspection
interface. It should consume the public API and initially support:

- Source and Page browsing;
- rendered Page Markdown;
- rendered Skill Markdown and parsed YAML metadata;
- folder-tree navigation;
- visibility into available MCP tools;
- later, governed editing and version history.

Authorization remains a server responsibility. The web application must not reproduce
domain or access-control rules in client code.

## Definition of Done for the Immediate Scope

- Data and access-control documents agree with the migration.
- A fresh PostgreSQL database upgrades to Alembic head successfully.
- Compose waits for PostgreSQL and migration completion before starting the API.
- The existing HTTP and mounted MCP health checks still pass.
- PostgreSQL integration tests cover the new schema constraints.
- HTTP and MCP authorization behavior is equivalent where the first protected operation
  exists.
- Ruff, formatting, Pyright, unit/E2E tests, integration tests, Compose configuration, and
  the Docker image build pass.
- README and agent context describe only behavior that was actually implemented.

## Explicitly Deferred

- the Next.js web console;
- production identity-provider integration;
- semantic ranking and external embedding providers;
- document parsing or agent-driven ingestion;
- MCP delivery of binary brand assets;
- deployment and production configuration.
