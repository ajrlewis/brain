# Commands

## Current State

No project commands are established yet. The repository has no application code, `pyproject.toml`, `uv.lock`, Docker configuration, test configuration, or CI workflow. Do not present the example commands in `README.md` as runnable until implementation adds and verifies them.

## Verified Host Tools

Verified during coding-agent bootstrap on 2026-09-12:

```text
git 2.50.1
gh 2.97.0
Python 3.12.0
uv 0.10.6
Docker 20.10.8
Docker Compose 2.0.0
```

The target application requires Python 3.13 or newer, so the currently selected `python3` does not satisfy the declared runtime requirement.

## Baseline To Establish With Implementation

When application scaffolding is separately authorized, add and verify ecosystem-native commands for dependency sync, local PostgreSQL, migrations, API and MCP development, Ruff lint and format checks, Pyright, focused/unit/integration/end-to-end tests, coverage, full verification, and Docker builds. Record only commands that have actually run successfully, including prerequisites and any required environment.
