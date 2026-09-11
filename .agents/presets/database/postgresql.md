# PostgreSQL Preset

Adopted for Brain with pgvector. Canonical Pages, Sources, Skills, and immutable versions must remain valid independently of rebuildable chunk and embedding data.

- Treat schema changes as migrations, not ad hoc database edits.
- Keep constraints, indexes, and transactions aligned with application invariants.
- Prefer explicit column types and constraints over relying only on application validation.
- Consider lock behavior and data volume for production migrations.
- Never commit credentials or connection strings with secrets.
- Record database setup and verification commands in `.agents/COMMANDS.md`.
