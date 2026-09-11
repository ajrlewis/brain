# PostgreSQL MCP Capability

Adopted for Brain's intended PostgreSQL + pgvector persistence boundary when local schema, migrations, and tests cannot answer a task. Default to disposable development data and read-only inspection.

## Capability

PostgreSQL database access.

## Purpose

Useful for inspecting schema, validating migrations, checking query behavior, and understanding data constraints.

## Requirement

Optional by default. Required only when repository-local schema and tests are insufficient for the task.

## Expected Scope

Prefer read-only access unless the task explicitly requires writes. Use separate development or staging databases when possible.

## Configuration

Connection details should come from environment variables or the agent host's secret store.

## Security Notes

Never commit database URLs, passwords, tokens, or production credentials.
