# Completed Agent TODOs

Completed persistent setup work, newest first. This is not a changelog or product backlog.

## Completed Items

- 2026-09-13 — Added stale-safe Page and Skill version publication, tenant-safe immutable Skill persistence, shared HTTP/MCP Skill and bounded inventory operations, worker-thread offloading for synchronous MCP database services, and the explicit idempotent five-Skill default bundle seed. Verified clean migration and zero metadata drift, transport parity, local-divergence preservation, quality checks, PostgreSQL integration, Compose rendering, and the Docker image.
- 2026-09-12 — Implemented the first governed knowledge slice: tenant-safe Folder, Source, Page, immutable PageVersion, and provenance persistence; shared HTTP/MCP create/read services with provenance intersection; and an idempotent synthetic Northstar seed.
- 2026-09-12 — Added the first Alembic migration and PostgreSQL-backed identity/access-control foundation, including tenant-safe constraints, explicit Compose migration ordering, and shared HTTP/MCP local bearer authentication.
- 2026-09-12 — Replaced the failing Docker Desktop 20.10.8 engine with Docker Desktop 4.90.0 (engine 29.7.2), initialized PostgreSQL 17 with pgvector 0.8.6, and passed the dependency-backed integration test. Made the Compose host port configurable because native PostgreSQL occupies port 5432 on this host.
- 2026-09-12 — Established the Python 3.13 uv workspace, typed configuration, shared health service, FastAPI and FastMCP entrypoints, pgvector Compose definition, Dockerfile, Ruff, Pyright, pytest/coverage, and GitHub Actions foundation. Verified dependency sync, both application commands, static checks, five focused tests at 94.87% coverage, Compose rendering, and the application image build. Local PostgreSQL runtime verification was initially blocked by the old host Docker engine and was later resolved above.
