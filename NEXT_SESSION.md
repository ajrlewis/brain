# Next Session

## Objective

Migrate Brain's complete runtime database boundary from synchronous SQLAlchemy/psycopg
execution and worker-thread offloading to native async I/O. The target deployment remains
one Brain/Cortex stack for one customer Organization with roughly 400 potential users.

This is a coordinated boundary change, not a route-signature edit. FastAPI and FastMCP
must directly await the same async application services, and those services must use
SQLAlchemy `AsyncSession` through async repositories. Preserve all authorization,
transaction, tenant-isolation, immutable-history, and optimistic-concurrency behavior.

Alembic migrations and explicit administrative seed commands are offline processes and may
remain synchronous. Do not retain a second synchronous runtime repository/service path.

## Immediate Scope

### 1. Async database foundation

- Add a runtime SQLAlchemy async engine using psycopg's async support and an
  `async_sessionmaker[AsyncSession]`.
- Replace the runtime `SessionFactory` and `session_scope` contracts with async equivalents,
  including commit, rollback, and close behavior.
- Keep a clearly named synchronous engine/session utility only where Alembic or explicit
  seed commands require it; document that it is not an application request path.
- Add typed environment settings for connection-pool size, overflow, acquisition timeout,
  connection recycling, and PostgreSQL statement/lock timeouts. Choose conservative
  defaults for a single-Organization deployment and explain how they relate to database
  connection limits rather than to the raw count of 400 users.
- Preserve one session per operation. Never share an `AsyncSession` across concurrent tasks.

### 2. Async repositories and services

- Convert every runtime identity, knowledge, and Skill repository database operation to
  `async def`, awaiting `scalar`, `scalars`, `execute`, `flush`, and transaction work.
- Convert every runtime service method that reaches persistence to `async def` and await its
  repository. Keep pure CPU-only validation helpers synchronous.
- Preserve Page and Skill row locking with `SELECT ... FOR UPDATE`; compare
  `expected_current_version_id` while holding the lock and commit the new immutable version
  plus current pointer atomically.
- Preserve authorization-before-disclosure, provenance intersection, same-tenant reference
  checks, bounded inventory queries, YAML validation, original Markdown bytes, and stable
  path behavior.
- Keep seed idempotency and read-only bundle review behavior unchanged.

### 3. Async HTTP and MCP transports

- Convert database-backed FastAPI handlers to `async def` and directly await shared services.
- Convert FastMCP database tools to directly await the same services.
- Remove `anyio.to_thread.run_sync` and the temporary MCP worker-offload helper after no
  runtime service beneath either transport performs blocking database I/O.
- Keep health and provider-neutral local authentication simple; do not make pure synchronous
  work async merely for visual consistency.
- Preserve equivalent HTTP/MCP allow, deny, missing, validation, duplicate, and stale-conflict
  behavior.

### 4. Concurrency and load verification

- Add deterministic tests proving async session commit, rollback, close, and task isolation.
- Add PostgreSQL tests that race two Page writers and two Skill writers from the same base.
  Exactly one mutation must become current; the loser must conflict; history must contain no
  unreviewed or partially committed version.
- Add concurrent HTTP and MCP integration tests using real PostgreSQL connections. Exercise
  at least 100 in-flight reads across Page, Source, Skill, and inventory operations, including
  authorized and denied requests.
- Include an event-loop responsiveness check while database requests are in flight so a
  hidden blocking driver or repository call fails deterministically.
- Exercise a pool smaller than the in-flight request count to prove requests wait safely
  without session sharing or connection exhaustion. Verify pool-acquisition and statement
  timeouts return controlled failures rather than hanging indefinitely.
- Record the test machine, PostgreSQL/pgvector versions, concurrency, pool settings,
  throughput, latency percentiles, failures, and interpretation. Avoid brittle performance
  assertions in CI; assert correctness and responsiveness, and report measurements
  separately.

### 5. Documentation and operational stance

- Update `README.md`, `.agents/ARCHITECTURE.md`, `.agents/COMMANDS.md`, and dependency/runtime
  documentation to describe the native async request boundary and explicit pool controls.
- Document how operators size the application pool against the managed PostgreSQL connection
  budget when scaling processes or replicas.
- Keep the initial single-customer model and tenant-safe constraints. Do not add shared-SaaS
  tenant discovery or administration.
- Keep Brain a store/service. Do not add scheduling, Skill execution, autonomous agents, or
  lint orchestration.

## Definition Of Done

- No FastAPI or FastMCP request path performs synchronous database I/O or uses worker-thread
  offloading for a runtime service.
- Runtime repositories and persistence-backed services use one consistent `AsyncSession`
  boundary; offline migration/seed sync utilities are clearly separated.
- Concurrent stale Page and Skill writes deterministically publish exactly one winner while
  retaining valid immutable history.
- HTTP and MCP preserve equivalent authorization and error behavior under concurrent load.
- A 100+-request PostgreSQL-backed concurrency exercise passes with a deliberately smaller
  pool, responsive event loop, no leaked sessions/connections, and recorded measurements.
- Clean Alembic upgrade, zero metadata drift, default and Northstar seeds, bundle review,
  quality checks, integration tests, Compose startup/health, and Docker build pass.
- Documentation explains pool sizing for one Organization with roughly 400 potential users
  and distinguishes measured capacity from unsupported user-count claims.

## Explicitly Deferred

- Brain-owned schedules, autonomous agents, Skill execution, automatic semantic merges, and
  unreviewed writes;
- shared multi-tenant SaaS provisioning and cross-tenant administration;
- binary asset delivery, production identity-provider integration, search/chunks/embeddings,
  the Next.js console, and production deployment;
- horizontal autoscaling decisions until native async measurements establish per-process
  capacity and the managed PostgreSQL connection budget is known.
