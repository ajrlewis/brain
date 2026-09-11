# uv Preset

Adopted for Brain's intended Python workspace and single root lockfile. Do not create the workspace or record example invocations as verified until application scaffolding is requested.

- Use `uv` when the repository has adopted `pyproject.toml` plus `uv.lock` or maintainer direction.
- Prefer `uv sync` for environment setup.
- Use `uv run <command>` for project commands that need the managed environment.
- Use a `uv` workspace when multiple Python applications or libraries intentionally share dependency resolution and one lockfile. Keep a `pyproject.toml` in each real workspace member.
- Do not force independently released projects or incompatible dependency sets into one workspace merely for directory symmetry.
- Keep `uv.lock` updated when dependencies change.
- Do not mix dependency managers without an explicit project decision.
- Document verified install, test, lint, typecheck, and migration commands in `.agents/COMMANDS.md`.
