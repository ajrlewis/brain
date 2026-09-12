# Agent TODO

Persistent agent-managed setup work only; this is not the product backlog. Move completed entries to `DONE.md` with the completion date and outcome.

## Open Items

- Add Alembic and its first verified migration alongside the first authorized application schema; the health-only foundation has no schema to migrate.
- Decide whether external approving review is practical for this solo repository, then obtain explicit authorization to configure GitHub protection. Require pull requests and the existing `quality` and `docker` CI checks, and block direct/force pushes and branch deletion; verify the effective rules afterward.
