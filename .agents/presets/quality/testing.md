# Testing Preset

Adopted for Brain. In addition to ordinary behavior, tests must prove immutable versions, content deduplication, provenance, derived-data rebuildability, equivalent HTTP/MCP rules, and authorization-safe search.

- Use fast, deterministic unit tests as the first verification layer for business rules, transformations, validation, and failure behavior.
- Add integration tests at real system boundaries such as databases, HTTP APIs, queues, filesystems, caches, and cloud adapters. Prefer disposable dependencies and deterministic seeded data over shared mutable environments.
- Keep the test pyramid intentional: many focused unit tests, enough integration tests to prove boundary behavior, and a small number of end-to-end tests for critical journeys when warranted.
- Test observable behavior and contracts rather than private implementation details. Mock owned boundaries deliberately; do not over-mock the behavior the test is meant to prove.
- Maintain high meaningful statement and branch coverage, especially for changed code and important failure paths. Use an explicit repository-appropriate threshold, but do not treat the percentage as proof of correctness.
- Every bug fix should include a regression test at the lowest layer that reliably reproduces it.
- Keep unit and integration suites independently runnable. Record focused, unit, integration, coverage, and full verification commands in `.agents/COMMANDS.md`.
- Run fast unit and static checks for pull requests. Run integration tests wherever their dependencies and isolation guarantees are available, and make skipped or unavailable coverage visible rather than silently passing.
- Keep fixtures synthetic, minimal, and readable. Never copy production credentials or sensitive production data into tests.
