# Agent TODO

Persistent agent-managed setup work only; this is not the product backlog. Move completed entries to `DONE.md` with the completion date and outcome.

## Open Items

- Review the four npm audit findings reported by the initial web dependency install (one
  moderate, two high, one critical), identify whether they affect production or only the
  OpenAPI/test toolchain, and upgrade without bypassing the pinned Next.js security release.

- Decide whether external approving review is practical for this solo repository, then obtain explicit authorization to configure GitHub protection. Require pull requests and the existing `quality` and `docker` CI checks, and block direct/force pushes and branch deletion; verify the effective rules afterward.
