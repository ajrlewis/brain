# Commands

## Prerequisites

The workspace selects Python from `.python-version` and requires Python 3.13+. uv 0.10.6,
Python 3.13.15, Docker 29.7.2, and Docker Compose 5.5.0 were used on 2026-09-12.
The explicit cache path below is required in restricted coding-agent environments and is
safe to use elsewhere.

## Workspace

Verified on 2026-09-13:

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

After migrating a local database, the deterministic synthetic knowledge seed is:

```bash
DATABASE_URL=postgresql+psycopg://brain:brain@localhost:5432/brain \
  UV_CACHE_DIR="$PWD/.uv-cache" uv run brain-seed-northstar
```

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
documents before proposing a bundled upgrade.

## Quality

Verified on 2026-09-13:

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run ruff check .
UV_CACHE_DIR="$PWD/.uv-cache" uv run ruff format --check .
UV_CACHE_DIR="$PWD/.uv-cache" uv run pyright
UV_CACHE_DIR="$PWD/.uv-cache" uv run pytest -m 'not integration' --cov --cov-report=term-missing
```

The last command ran 45 tests with 90%+ branch-aware coverage. The dependency-backed
integration suite is intentionally separate and ran 6 PostgreSQL tests:

```bash
TEST_DATABASE_URL=postgresql://brain:brain@localhost:5432/brain \
  UV_CACHE_DIR="$PWD/.uv-cache" uv run pytest -m integration
```

## PostgreSQL And Docker

The Compose model and application image build were verified on 2026-09-13:

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
