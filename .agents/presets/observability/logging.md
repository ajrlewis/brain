# Logging Preset

Adopted for Brain. Preserve incoming correlation IDs across HTTP/MCP, database, search, and embedding-provider boundaries; never log knowledge content, credentials, or hidden model reasoning unnecessarily.

- Use the repository's established logging facade. Keep initialization, formatting, enrichment, filtering, and sinks centralized rather than configuring loggers throughout application code.
- Document where logging is configured and the main observability boundaries in `.agents/ARCHITECTURE.md`; record exact local log and diagnostic commands in `.agents/COMMANDS.md`.
- Prefer structured events with stable names and fields in deployed environments. Include useful context such as service, environment, version, operation, correlation or trace ID, and relevant non-sensitive identifiers.
- Log meaningful boundaries: startup and shutdown, request or message completion, scheduled jobs, dependency calls, migrations, deployments, retries, and terminal failures. Avoid noisy line-by-line narration and duplicate error logging at every layer.
- Record an error where it is handled or allowed to cross an ownership boundary. Preserve the exception and actionable context without logging request bodies, query results, credentials, tokens, secrets, or unnecessary personal data.
- Define log levels consistently. Keep routine success at `info`, recoverable abnormal behavior at `warning`, failed operations at `error`, and verbose diagnostics at `debug`; do not depend on debug logging in production.
- Propagate correlation context across HTTP, queues, background jobs, database work, and pipeline stages where the stack supports it.
- Treat logs, metrics, and traces as complementary signals. Logging alone is not sufficient evidence of health or successful deployment.
- Make local logs easy to reach through the normal development entrypoint, such as Docker Compose, while keeping production retention, access, and redaction aligned with organizational policy.
- Test critical event emission and redaction behavior without coupling tests to entire formatted log lines.
