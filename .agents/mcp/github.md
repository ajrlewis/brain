# GitHub MCP Capability

Adopted for `ajrlewis/brain` repository metadata, pull requests, reviews, Actions, and protection inspection. Remote setting changes still require explicit maintainer authorization.

## Capability

GitHub repository access.

## Purpose

Useful for issues, pull requests, review comments, Actions/CI status, repository metadata, branches, tags, and releases.

## Requirement

Optional by default. Required only when the task depends on GitHub state that is not available in the local checkout.

## Expected Scope

Grant the narrowest access that supports the task: repository metadata, pull requests, issues, and workflow status where needed.

## Local Tooling

GitHub access may come from an MCP server, host integration, or the optional `gh` CLI. Require `gh` only when adopted commands use it for pull requests, branch rules, releases, or other GitHub API operations, and authenticate it outside the repository.

## Configuration

Host-specific MCP configuration varies. Use this file as the canonical capability intent and create only thin host adapters when required.

## Security Notes

Do not commit tokens, private keys, or credential values. Environment variable names are acceptable; secret values are not.
