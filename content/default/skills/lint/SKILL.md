---
name: lint
description: Audit Skill routing and knowledge quality through bounded read-only stages.
inputs:
  scope:
    type: object
    required: true
outputs:
  report:
    type: object
    required: true
  proposed_changes:
    type: array
    required: true
tools:
  - list_skills
  - get_skill_by_slug
  - list_pages
  - get_page
  - get_page_by_path
  - get_source
  - list_sources
---

# Lint

Run read-only by default. Brain supplies records; Cortex owns checkpoints, scheduling,
candidate selection, delegation, report combination, and any later approved mutations.

## Stages

1. List Skills. Validate every complete YAML frontmatter contract, declared input/output,
   and tool against the tools actually available. Read `index`; ensure every route resolves
   to a live current Skill, all non-index bundled Skills are reachable, and route declarations
   match the target contracts.
2. List Pages. Validate unique stable folder/Page paths. Resolve internal absolute Page links
   with `get_page_by_path`; report broken, ambiguous, or unavailable links. Check curated home
   navigation for important entry points, but treat generated inventory as authoritative.
3. Group inventory entries by current content hash and report exact duplicates without
   reading their bodies. Request only bounded semantic duplicate candidates from retrieval;
   never load the complete corpus merely to compare it.
4. Review bounded folders or candidate clusters. Cortex may delegate these independent
   clusters to subagents and combine compact findings without maximizing context windows.
5. Use `list_sources` freshness fields and bounded `get_source` reads. Report conflicting
   or superseded facts, missing provenance or current versions, stale
   Source revisions, and navigation/layout drift. Propose canonical merges that preserve all
   Source provenance and immutable histories.

Do not mutate during the audit. Every proposed merge, link rewrite, status change, or new
version requires human confirmation. After confirmation, re-read and recheck the expected
current version; stale approval is invalid and must return to review.
