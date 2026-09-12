# Next Session

## Objective

Build concurrency-safe Skill persistence and bootstrap Brain's repository-owned default
Skill bundle. A fresh single-tenant deployment should seed version-one `index`, `ingest`,
`retrieve`, `update`, and `lint` Skills without depending on client-specific instruction
files.

Brain stores and validates Skill documents. Cortex retrieves and executes them. The lint
Skill defines a governed, read-only-by-default audit workflow; Brain does not become a
scheduler or agent orchestrator.

## Immediate Scope

### 1. Optimistic version concurrency

Before adding more writers, make Page updates stale-safe:

- require `expected_current_version_id` when appending a PageVersion;
- lock the Page and reject a mutation whose expected version is no longer current;
- expose equivalent HTTP and MCP conflicts;
- preserve immutable history and never automatically semantic-merge concurrent edits.

Apply the same rule to Skill updates. Human approval is bound to the reviewed base version
and becomes invalid when that base is stale. Add narrowly scoped idempotency for retryable
mutations if it does not require a speculative job system.

### 2. Skill persistence and services

Implement the Skill and immutable SkillVersion contracts in `docs/DATA_MODEL.md` with a
new Alembic revision. Add explicit schemas, repositories, and shared services for focused
create/read/list/version operations. Preserve tenant-safe references, policy inheritance,
immutable content, hashes, and valid same-Skill current pointers.

Validate YAML frontmatter when a SkillVersion is created and expose the complete original
Markdown document. HTTP and MCP remain thin adapters over the same services.

### 3. Repository-owned default bundle

Add canonical seed content under:

```text
content/default/
├── manifest.yaml
└── skills/
    ├── index.md
    ├── ingest.md
    ├── retrieve.md
    ├── update.md
    └── lint.md
```

Package it into the Docker image. Add an explicit `brain-seed-defaults` command that
resolves the target Organization, policy, steward, and audit Principal. Stable identities
and hashes must make bootstrap repeatable. Rerunning it must not duplicate records or
overwrite a locally edited current SkillVersion. Bundled upgrades require an explicit
diff/review path, never implicit startup or migration behavior.

The `index` Skill is the stable routing entry point. It maps purposes to live Skill slugs,
declared inputs/outputs, and Brain tools without duplicating each Skill's instructions.
The other Skills only advertise operations Brain actually implements.

### 4. Lint and navigation contracts

Version one of `lint` defines a staged, read-only-by-default audit that:

- validates Skill frontmatter, available tools, index routing, reachability, and links;
- validates stable folder/Page paths and internal Page links;
- finds exact duplicates by hash and requests bounded semantic duplicate candidates rather
  than reading the complete corpus;
- proposes canonical merges while preserving provenance and immutable history;
- reports conflicting or superseded facts, missing provenance/current versions, stale
  Source revisions, and navigation/layout drift;
- treats a compact curated home Page as an entry point, while generated inventory remains
  authoritative for exhaustive navigation;
- permits Cortex to delegate bounded folder or candidate clusters to subagents and combine
  compact findings, without maximizing every context window;
- requires human confirmation for changes, followed by an expected-version recheck.

Add only the minimal list/inventory and stable-path operations the default Skills need.
Do not implement scheduling inside Brain. A scheduled Cortex process may retrieve `lint`,
run checkpoints, present proposed changes, and apply approved changes through Brain.

### 5. Deployment and execution stance

Treat one Brain/Cortex stack with one active customer Organization as the initial
deployment model. Retain tenant-safe constraints for defense in depth and synthetic tests;
do not build shared-SaaS tenant discovery or administration.

The current SQLAlchemy/psycopg path is synchronous. Keep this Skill slice focused, but
measure concurrent HTTP and MCP database behavior and record a concrete async decision.
Before high-fanout linting, either migrate the entire shared boundary to SQLAlchemy
`AsyncSession` with psycopg async, or consistently offload synchronous services in both
transports. Do not mix ad hoc sync and async repositories.

## Definition Of Done

- Page and Skill stale writes conflict without moving the current pointer or losing history.
- A clean PostgreSQL upgrade has no metadata drift and tests prove Skill constraints.
- HTTP and MCP Skill operations have equivalent allow, deny, missing, and conflict behavior.
- `brain-seed-defaults` creates five version-one Skills and safely preserves local divergence.
- Deterministic lint tests catch broken routes, frontmatter, tools, paths, links, and exact
  duplicates.
- Large-corpus tests prove lint selection is bounded by inventory/folders/retrieval candidates.
- Relevant quality, PostgreSQL, Compose, and Docker checks pass.
- Documentation distinguishes implemented behavior from deferred orchestration and async work.

## Explicitly Deferred

- Brain-owned schedules, autonomous agents, automatic semantic merges, and unreviewed writes;
- shared multi-tenant SaaS provisioning and cross-tenant administration;
- binary asset delivery and production identity-provider integration;
- broad async conversion unless selected and completed across the shared service boundary;
- the Next.js console and production deployment.
