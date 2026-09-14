# Workflow

`README.md` defines the Mind product workspace. `products/brain/README.md` is Brain's
target-state product specification, and `products/cortex/README.md` is the Cortex specification.
`.agents/ARCHITECTURE.md` records implemented slices; do not describe specifications as
implemented or proposed commands as verified.

## Change Loop

1. Read the relevant product specification, current implementation, tests, and agent guidance.
2. Preserve Brain's agent-agnostic storage boundary and make the smallest change that satisfies the task.
3. Add or update focused tests for changed behavior, including failure and authorization paths where relevant.
4. Run the relevant verified commands from `.agents/COMMANDS.md`.
5. Review the diff for scope, secrets, generated files, migrations, and documentation accuracy.
6. Update agent context only when durable project facts change. Record persistent out-of-scope setup work in `.agents/todos/TODO.md` and archive completed entries in `DONE.md`.

## Python And TypeScript Changes

- Python applications and packages use uv, Ruff, Pyright, and pytest. Brain tests live in
  `products/brain/tests/`, with dependency-backed PostgreSQL behavior behind the `integration` marker.
- The TypeScript applications are npm workspaces at `products/brain/apps/web` and
  `products/cortex/apps/web`. Use ESLint, TypeScript's
  no-emit check, Vitest with Testing Library for components and server transport behavior,
  and Playwright for browser integration with the real Compose API and Northstar seed.
- FastAPI schemas are authoritative. Regenerate `products/brain/apps/web/openapi.json` and the generated Zod
  validators after public API changes; never hand-edit generated contracts. The drift check
  must pass in CI.
- Keep backend tokens and local credential validation in server-only modules. Client
  Components are limited to browser interaction and must not import server configuration.
- Run checks for every language affected by a change. Cross-stack contracts, Docker, Compose,
  or browser behavior require both Python and TypeScript checks plus the relevant integration
  flow.

## Git

The repository uses GitHub Flow with `main` as the remote default branch.

- Work on a focused feature or fix branch; never push directly to `main`.
- Use a concise typed branch name such as `feature/add-export`, `fix/empty-response`, or `chore/update-dependencies`; include a tracker identifier when one exists.
- Before pushing or updating a pull request, fetch `origin` and merge `origin/main` into the feature branch. Resolve conflicts on the feature branch and rerun relevant checks.
- Open a pull request into `main`, inspect CI and review feedback, and merge through the pull request.
- Do not force-push shared branches.

The phrases "branch add commit push and PR" and "PR merged," or clear equivalents, invoke the complete delivery and safe local-cleanup procedures in `.agents/presets/git/github-flow.md`. Do not pause between authorized delivery steps merely to request confirmation already supplied by the shortcut.

The remote is a solo repository with no current protection on `main`. Follow the corresponding open item in `.agents/todos/TODO.md`; remote repository-setting changes require explicit maintainer authorization.

## Project-Specific Expectations

- Keep HTTP and MCP as thin interfaces over the same domain/application services.
- Define schema changes with Alembic migrations and validate them against PostgreSQL with pgvector where behavior depends on those systems.
- Keep configuration typed and environment-based; never commit secrets.
- Update public contracts and focused architecture documents alongside behavior changes.
- Keep fixtures synthetic. The Northstar example must not contain real confidential information.
- Require explicit maintainer authorization before deployments, production access, database mutations outside normal local/test workflows, secret changes, or remote repository-setting changes.
