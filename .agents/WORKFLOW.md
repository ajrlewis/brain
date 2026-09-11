# Workflow

`README.md` is Brain's target-state product specification. The repository currently contains no application implementation, so do not describe planned components as existing or proposed commands as verified. Application scaffolding requires a separate request.

## Change Loop

1. Read the relevant parts of `README.md`, the current implementation, tests, and agent guidance.
2. Preserve Brain's agent-agnostic storage boundary and make the smallest change that satisfies the task.
3. Add or update focused tests for changed behavior, including failure and authorization paths where relevant.
4. Run the relevant verified commands from `.agents/COMMANDS.md`.
5. Review the diff for scope, secrets, generated files, migrations, and documentation accuracy.
6. Update agent context only when durable project facts change. Record persistent out-of-scope setup work in `.agents/todos/TODO.md` and archive completed entries in `DONE.md`.

## Git

The repository uses GitHub Flow with `main` as the remote default branch.

- Work on a focused feature or fix branch; never push directly to `main`.
- Before pushing or updating a pull request, fetch `origin` and merge `origin/main` into the feature branch. Resolve conflicts on the feature branch and rerun relevant checks.
- Open a pull request into `main`, inspect CI and review feedback, and merge through the pull request.
- Do not force-push shared branches.

The remote is currently a solo repository with no commits, so `main` and effective branch protection do not yet exist. Follow the corresponding open item in `.agents/todos/TODO.md` after the initial branch is published.

## Project-Specific Expectations

- Keep HTTP and MCP as thin interfaces over the same domain/application services.
- Define schema changes with Alembic migrations and validate them against PostgreSQL with pgvector where behavior depends on those systems.
- Keep configuration typed and environment-based; never commit secrets.
- Update public contracts and focused architecture documents alongside behavior changes.
- Keep fixtures synthetic. The Northstar example must not contain real confidential information.
- Require explicit maintainer authorization before deployments, production access, database mutations outside normal local/test workflows, secret changes, or remote repository-setting changes.
