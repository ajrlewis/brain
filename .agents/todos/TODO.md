# Agent TODO

Persistent agent-managed setup work only; this is not the product backlog. Move completed entries to `DONE.md` with the completion date and outcome.

## Open Items

- Establish and verify the project quality baseline when application scaffolding is authorized: Python 3.13+, dependency sync, Ruff, Pyright, unit/integration/end-to-end tests, meaningful coverage, PostgreSQL + pgvector integration, migrations, Docker build, and GitHub Actions. Then replace the placeholder state in `.agents/COMMANDS.md` with exact verified commands.
- After the first commit creates remote `main`, decide whether external approving review is practical for this solo repository, then obtain explicit authorization to configure GitHub protection. Require pull requests and block direct/force pushes and branch deletion; add relevant required checks once CI exists, and verify the effective rules afterward.
