# Agent TODO

Persistent agent-managed setup work only; this is not the product backlog. Move completed entries to `DONE.md` with the completion date and outcome.

## Open Items

- Evaluate and migrate the repository-owned default Skill bundle from its current flat document
  layout to conventional per-Skill directories (for example `skills/index/SKILL.md` and
  `skills/index/references/governance.md`). Preserve deterministic manifest ordering, exact
  Markdown bytes, idempotent seed upgrades, and read-only bundle review behavior.
- Decide whether external approving review is practical for this solo repository, then obtain explicit authorization to configure GitHub protection. Require pull requests and the existing `quality` and `docker` CI checks, and block direct/force pushes and branch deletion; verify the effective rules afterward.
