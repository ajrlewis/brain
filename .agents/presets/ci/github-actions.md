# GitHub Actions Preset

Adopted for Brain's CI. Pull requests and `main` run Ruff, Pyright, pytest with PostgreSQL + pgvector, and a Docker build without production credentials.

- Keep CI close to the commands developers run locally.
- Pin actions sensibly and avoid unnecessary secrets exposure.
- Use least-privilege permissions for workflows.
- Cache dependencies only when it is correct and measurable.
- Keep required checks focused on build, test, lint, typecheck, and security checks that matter for the project.
- Inspect failing workflow logs before guessing at fixes.
