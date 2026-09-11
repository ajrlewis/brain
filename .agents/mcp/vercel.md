# Vercel MCP Capability

Adopted for Brain's intended production host once a Vercel project exists. Repository code remains canonical; deployments and hosted configuration changes require explicit maintainer authorization.

## Capability

Vercel project, deployment, log, and documentation access.

## Purpose

Useful for inspecting linked projects, deployment status, build or runtime logs, environment metadata, and platform documentation when repository-local configuration is insufficient.

## Requirement

Optional by default. Required only when Vercel-hosted state affects the task and cannot be inferred from the repository, local verification, or CI.

## Source Of Truth

Keep application code and deployment configuration in the repository. Treat Vercel as the source of truth for live deployment state. Keep secret values in an explicitly adopted external secret store or Vercel environment configuration, never in repository files.

## Git And CI/CD

When Git-based CI is adopted, require relevant CI checks before merging into the production branch. For GitHub-connected projects, prefer Vercel Deployment Checks so a production deployment is not promoted or assigned to production domains until the selected GitHub Actions succeed. Treat bypassing these checks as a production-affecting action that requires explicit authorization.

## Expected Scope

Prefer access limited to the relevant account, team, and project. Read deployments and logs as needed. Creating, promoting, rolling back, or cancelling deployments, changing domains or project settings, editing environment variables, or affecting production requires explicit authorization.

## Local Tooling

Vercel's hosted remote MCP server does not require the `vercel` CLI. Adopt the CLI only when project commands use it for local environment retrieval, builds, logs, or deployment operations. Keep its installation and authentication outside the repository.

## Configuration

Prefer Vercel's official OAuth-based MCP endpoint, `https://mcp.vercel.com`, when the agent host supports it. Verify its current maturity, available tools, and effective access before relying on it. Keep host-specific connection state outside the repository and record exact verified CLI commands in `.agents/COMMANDS.md` only when the project adopts them.

See the official [Vercel MCP documentation](https://vercel.com/docs/agent-resources/vercel-mcp).

## Security Notes

Connecting the MCP server grants access derived from the authenticated Vercel user. Use a narrowly scoped account where practical. Do not expose environment values, access tokens, private logs, customer data, or deployment secrets in repository files or agent output.
