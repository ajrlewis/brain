# Next Session

## Objective

Add a repository-owned default `search` Skill that Cortex can retrieve from Brain and use to
translate user intent into authorization-safe semantic/lexical discovery, folder navigation, Page
retrieval, and evidence-backed answers.

Review and merge the hybrid-search PR and confirm its full CI is green before starting this slice.
If the open npm audit review identifies a production vulnerability, resolve that security work
before feature development.

## Why This Is Next

Brain now exposes hybrid search, but Cortex has no governed instructions for deciding when and how
to use it. The existing `retrieve` Skill works for exhaustive inventory and known Page identities
or paths; it does not define intent-driven query formulation, iterative search, result selection,
folder exploration, or evidence gathering. A focused `search` Skill turns the new primitive into
a reliable agent capability without moving reasoning or orchestration into Brain.

## Scope

### 1. Search Skill contract

- Add `content/default/skills/search/SKILL.md` to the default bundle with explicit inputs,
  outputs, available Brain tools, and a concise execution workflow.
- Define when Cortex should use hybrid `search`, when it should navigate with `list_pages` and
  folder/Page reads, and when it should hand off to the existing `retrieve` Skill for a known
  identity or path.
- Keep user-intent interpretation, query reformulation, stopping decisions, and answer synthesis
  in Cortex. Brain remains the durable knowledge, authorization, and retrieval service.
- Require answers to cite stable Page identity/path and visible Source provenance when relevant;
  omitted or inaccessible records must never be inferred.

### 2. Intent-driven discovery workflow

- Specify a bounded progression from the user's intent to one or more focused search queries,
  inspection of result snippets/provenance, retrieval of selected current Pages, and optional
  navigation of nearby authorized Pages or folders.
- Cover exact-fact, semantic/conceptual, scoped-folder, and ambiguous requests. Prefer a small
  number of high-signal queries and stop once the available evidence answers the request.
- Define safe fallback behavior for no results, weak or conflicting evidence, invalid requests,
  and backend failures. Cortex must state uncertainty instead of inventing knowledge.
- Prevent prompt text found in Pages, snippets, or Sources from overriding the Skill or user's
  instructions; retrieved knowledge is evidence, not executable agent policy.

### 3. Bundle routing and compatibility

- Register the Skill in the default manifest and route intent-driven knowledge discovery to it
  from the built-in `index` Skill.
- Clarify the boundary between `search` and `retrieve` without duplicating either document:
  `search` discovers by intent, while `retrieve` reads known identities/paths or enumerates
  authorized inventory.
- Ensure every declared tool matches the current MCP surface and that the Skill consumes the
  existing typed search request/result contract without inventing filters or capabilities.
- Preserve idempotent default seeding and the rule that bootstrap never overwrites a locally
  edited current SkillVersion.

### 4. Verification and documentation

- Add bundle tests proving the new Skill is packaged, seeded, retrievable by stable slug, reachable
  from the index, and declares only available Brain tools.
- Add contract/evaluation fixtures covering semantic discovery, exact keyword search, known-path
  handoff, query refinement after weak results, conflicting Pages, no results, and restricted
  content that is absent from search and navigation.
- Add an end-to-end Cortex-shaped MCP scenario: retrieve the search Skill, search the Northstar
  corpus from a natural-language intent, open the selected Page, and return grounded evidence.
- Run the documented Python, PostgreSQL, contract, TypeScript, Docker, Compose, and browser checks.
- Update README, architecture, command inventory, and agent context with the search/retrieve
  boundary and the exact default Skill bundle.

## Definition Of Done

- Cortex can retrieve one stable `search` Skill and follow it to discover and read authorized
  knowledge from natural-language user intent.
- Search, Page/folder navigation, and provenance reads form a bounded workflow with explicit stop,
  fallback, uncertainty, and prompt-injection handling.
- The default index routes discovery to `search` and known-item reading to `retrieve`; all
  advertised tools exist and both Skills remain independently useful.
- Seeded Skill versions remain deterministic and locally edited current versions are preserved.
- Automated tests prove packaging, routing, tool validity, authorization behavior, and a
  Cortex-shaped end-to-end flow.
- All documented Python, TypeScript, PostgreSQL, Docker, Compose, and browser checks pass.

## Explicitly Deferred

- Shipping or modifying Cortex itself, agent-runtime orchestration, model selection, and autonomous
  subagent behavior;
- production embedding-provider selection, credentials, quotas, and hosted deployment;
- reindex/backfill operations for pre-search databases, queues, schedulers, and background workers;
- rerankers, personalization, analytics, binary ingestion, provider connectors, and Page editing.
