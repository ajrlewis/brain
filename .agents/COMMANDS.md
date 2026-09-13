# Commands

## Prerequisites

The workspace selects Python from `.python-version` and requires Python 3.13+. uv 0.10.6,
Python 3.13.15, Docker 29.7.2, and Docker Compose 5.5.0 were used on 2026-09-12.
The explicit cache path below is required in restricted coding-agent environments and is
safe to use elsewhere.

## Workspace

Verified on 2026-09-14:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv lock
UV_CACHE_DIR="$PWD/.uv-cache" uv sync --frozen --all-packages
```

## Applications

Verified on 2026-09-13. The API health response was queried at
`http://127.0.0.1:8000/health`, MCP Streamable HTTP is mounted at
`http://127.0.0.1:8000/mcp/`, and the MCP command reached its stdio serving loop.

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run brain-api
UV_CACHE_DIR="$PWD/.uv-cache" uv run brain-mcp
```

Register the running local HTTP MCP endpoint with Codex while keeping the bearer token in the
client process environment:

```bash
export BRAIN_MCP_TOKEN=brain-local-dev
codex mcp add brain-local \
  --url http://127.0.0.1:8000/mcp/ \
  --bearer-token-env-var BRAIN_MCP_TOKEN
codex mcp get brain-local
```

Open a new Codex session to discover the tools. `codex mcp remove brain-local` removes the
host-local registration. This changes the user's Codex configuration, not repository state.

After migrating a local database, the deterministic synthetic knowledge seed is:

```bash
DATABASE_URL=postgresql+psycopg://brain:brain@localhost:5432/brain \
  UV_CACHE_DIR="$PWD/.uv-cache" uv run brain-seed-northstar
```

The command reads `examples/northstar/seed/manifest.yaml` plus its referenced UTF-8
documents. It performs no downloads and can be rerun without duplicating identities,
versions, provenance, or deterministic derived chunks.

Seed the repository-owned default Skill bundle explicitly after resolving deployment
identities (these selectors match Northstar):

```bash
DATABASE_URL=postgresql+psycopg://brain:brain@localhost:5432/brain \
  UV_CACHE_DIR="$PWD/.uv-cache" uv run brain-seed-defaults \
  --organization northstar \
  --policy "Northstar organization-wide" \
  --steward northstar-alex \
  --audit-principal northstar-cortex
```

Add `--review` to print a read-only unified diff between bundled and deployed current
`SKILL.md` documents before proposing a bundled upgrade. The conventional Skill directories
and supporting references are included in the `brain-db` wheel and Docker build.

## Quality

Verified on 2026-09-14:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run ruff check .
UV_CACHE_DIR="$PWD/.uv-cache" uv run ruff format --check .
UV_CACHE_DIR="$PWD/.uv-cache" uv run pyright
UV_CACHE_DIR="$PWD/.uv-cache" uv run pytest -m 'not integration' --cov --cov-report=term-missing
```

The last command ran 58 tests with 90%+ branch-aware coverage. The dependency-backed
integration suite is intentionally separate and includes PostgreSQL stale-writer races,
timeout behavior, and a 100-request HTTP/MCP concurrency exercise with a five-connection pool:

```bash
TEST_DATABASE_URL=postgresql://brain:brain@localhost:5432/brain \
  UV_CACHE_DIR="$PWD/.uv-cache" uv run pytest -m integration
```

The suite ran 10 PostgreSQL tests on 2026-09-14, including hybrid-search authorization,
current-version, clean-migration, and HTTP/MCP parity coverage.

The concurrency test reports elapsed time, throughput, and p50/p95 request latency without
asserting machine-specific performance thresholds. It does assert authorization/correctness,
event-loop progress, controlled pool/statement timeouts, and zero checked-out connections.

Measurement recorded 2026-09-13 on macOS 26.3.1 x86_64 with Docker 29.7.2,
PostgreSQL 17.11, and pgvector 0.8.6: 100 simultaneous in-process ASGI requests (50 HTTP,
50 MCP; Page, Source, Skill, and inventory reads; 20 expected authorization denials) used
pool size 5 with zero overflow and completed in 1.807 seconds, 55.4 requests/second, p50
706.5 ms, p95 1694.3 ms, and zero unexpected failures or checked-out connections afterward.
The event-loop probe progressed throughout. Separate pool size 2 checks used 50 ms pool
acquisition and statement timeouts and returned controlled exceptions. These local synthetic
measurements verify bounded concurrency behavior; they are not a production capacity or
400-concurrent-user claim.

## Web console

```bash
npm install
npm run web:contracts:check
npm run web:lint
npm run web:typecheck
npm run web:test
npm run web:build
npm run test:e2e --workspace @brain/web
```

`web:test` runs Vitest unit/component and mocked server-transport tests. The Playwright browser
integration expects a running, migrated, Northstar-seeded Compose stack. Prepare it with:

```bash
docker compose up -d --build
docker compose exec -T api brain-seed-northstar
npx playwright install chromium
npm run test:e2e --workspace @brain/web
```

Contract generation, lint, type checking, 19 unit/component tests, production builds,
Compose health, Northstar seeding, and the Playwright Page/provenance/search flow were verified
on 2026-09-14. Docker Desktop's BuildKit path transiently corrupted a bytecode input during one
build; the documented `DOCKER_BUILDKIT=0 docker compose build` fallback completed successfully.

## PostgreSQL And Docker

The Compose model and application image build were verified on 2026-09-14:

```bash
docker compose config
docker build -t brain:knowledge .
```

Run the combined FastAPI and FastMCP HTTP application with PostgreSQL:

```bash
docker compose up -d --build
docker compose ps
docker compose down
```

Canonical local database lifecycle:

```bash
docker compose up -d postgres
docker compose exec -T postgres pg_isready -U brain -d brain
docker compose up migrate
docker compose up -d api
docker compose exec -T postgres psql -U brain -d brain -c \
  "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
docker compose down
```

For a host-run migration instead of the one-shot container:

```bash
DATABASE_URL=postgresql+psycopg://brain:brain@localhost:5432/brain \
  UV_CACHE_DIR="$PWD/.uv-cache" uv run alembic upgrade head
```

If host port 5432 is already occupied, select another port consistently for Compose and
the test connection:

```bash
POSTGRES_PORT=55432 docker compose up -d postgres
TEST_DATABASE_URL=postgresql://brain:brain@localhost:55432/brain \
  UV_CACHE_DIR="$PWD/.uv-cache" uv run pytest -m integration
POSTGRES_PORT=55432 docker compose down
```

To erase local Brain database data, use `docker compose down -v`. This permanently removes
the disposable Compose volume.

The database lifecycle, clean Alembic upgrade, model/migration comparison, integration
tests, one-shot migration dependency, healthy API, and image build were verified on
2026-09-13 with Docker Desktop 4.90.0 using
host port 55432 because a native PostgreSQL instance occupies 5432. Docker Desktop 20.10.8
had previously failed during `initdb` with `Cannot allocate memory`. CI also performs the
extension creation and integration test on Linux.
