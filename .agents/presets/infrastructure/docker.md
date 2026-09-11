# Docker Preset

Adopted for Brain's host-independent service and local PostgreSQL + pgvector dependency. Northstar fixtures must stay synthetic, and container behavior must match direct local execution.

- Keep images small, reproducible, and aligned with the repository's runtime choices.
- Prefer Docker Compose as the single local entrypoint when the application needs supporting services. Include only dependencies required for realistic local development and tests.
- Avoid baking secrets into images or compose files.
- Separate development conveniences from production runtime requirements.
- Use health checks and startup dependencies so migrations and seed steps do not race services that are not ready.
- Provide an explicit, repeatable seed command with small synthetic fixtures. Never copy production data into the local stack.
- Keep local database volumes disposable and document the reset command and its data-loss effect before expecting an agent to use it.
- Rebuild and run the relevant services after Dockerfile or compose changes.
- Record canonical Compose start, stop, reset, migrate, seed, test, and log commands in `.agents/COMMANDS.md`.
