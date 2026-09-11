# GitHub Actions Preset

Adopted for Brain's intended CI. Pull requests and the default branch should eventually run Ruff, Pyright, pytest (including PostgreSQL + pgvector integration coverage), and a Docker build without production credentials.

- Keep CI close to the commands developers run locally.
- Pin actions sensibly and avoid unnecessary secrets exposure.
- Use least-privilege permissions for workflows.
- Cache dependencies only when it is correct and measurable.
- Keep required checks focused on build, test, lint, typecheck, and security checks that matter for the project.
- Inspect failing workflow logs before guessing at fixes.
