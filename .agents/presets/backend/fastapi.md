# FastAPI Preset

Adopted for Brain's HTTP interface. FastAPI routes must delegate to the same domain/application services used by MCP and must not own versioning, authorization, or search rules.

- Keep request and response schemas explicit. Prefer the project's established Pydantic conventions; when no alternative exists, Pydantic is the native default for FastAPI boundary models.
- Put validation at API boundaries and business rules in service/domain code.
- Do not use transport validation models as a substitute for domain rules, authorization, or database constraints.
- Use dependency injection for shared resources such as settings, database sessions, and auth context.
- Avoid import-time network or database work.
- Keep route handlers thin enough that behavior can be tested without HTTP where practical.
- Document local server, test, and integration commands in `.agents/COMMANDS.md`.
