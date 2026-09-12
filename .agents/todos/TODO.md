# Agent TODO

Persistent agent-managed setup work only; this is not the product backlog. Move completed entries to `DONE.md` with the completion date and outcome.

## Open Items

- Re-run the PostgreSQL + pgvector integration command on a working local Docker engine. Docker Desktop 20.10.8 on the 2026-09-12 host reproducibly failed to fork PostgreSQL during `initdb` with `Cannot allocate memory`; the image itself and Compose model were valid.
- Add Alembic and its first verified migration alongside the first authorized application schema; the health-only foundation has no schema to migrate.
- After the first commit creates remote `main`, decide whether external approving review is practical for this solo repository, then obtain explicit authorization to configure GitHub protection. Require pull requests and block direct/force pushes and branch deletion; add relevant required checks once CI exists, and verify the effective rules afterward.
