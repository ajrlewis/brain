# Monorepo Preset

Adopted for Brain's Python monorepo. The persistent identity/access-control foundation implements `apps/api`, `apps/mcp`, and the responsibility-based `packages/` boundaries below; knowledge, Skill, and search behavior remains target state.

```text
apps/
├── api/                  HTTP interface
└── mcp/                  MCP interface

packages/
├── core/                 domain behavior
├── db/                   persistence
├── ai/                   provider-neutral embedding boundary
├── search/               authorized retrieval
├── auth/                 authorization context
└── schemas/              shared public contracts
```

- Create only directories that represent real components. The names above are conventional examples, not mandatory empty scaffolding.
- Treat each `apps/` child as an independently runnable or deployable product boundary with explicit configuration, entrypoints, ownership, and verification.
- Put genuinely reusable code in focused `packages/` modules with deliberate public APIs. Do not create a generic `shared`, `common`, or `utils` dumping ground.
- Keep dependency direction clear: applications may depend on packages; packages must not reach into applications; avoid cyclic package dependencies.
- Extract a package when a stable domain or technical boundary justifies it, not merely because code might be reused later.
- Keep one root workspace definition and lockfile where the ecosystem supports it. Centralize truly shared tool configuration while allowing application-specific configuration where behavior differs.
- Keep cross-interface contracts explicit and derived from one domain definition rather than independently implementing HTTP and MCP behavior.
- Keep tests close to the code they verify. Share test helpers only when they represent a real reusable testing capability.
- Define root commands for focused application or package work and for full-repository verification. Record exact workspace filters, dependency order, build, test, lint, typecheck, and development commands in `.agents/COMMANDS.md`.
- Let CI use affected-component optimization only when dependency detection is trustworthy; retain full verification for release and other high-risk paths.
- Keep repository-wide infrastructure in a clear root boundary such as `infra/` when it is not owned by one application, and document deployment ownership in `.agents/ARCHITECTURE.md`.
- Use a `uv` workspace for shared dependency resolution and one lockfile. Add task orchestration only if real complexity justifies it.
- Document the actual workspace tree, dependency direction, shared package contracts, and deployment boundaries in `.agents/ARCHITECTURE.md` after discovery.
