---
name: ingest
description: Store supplied extracted Markdown as governed Pages with Source provenance.
inputs:
  source:
    type: object
    required: true
  pages:
    type: array
    required: true
outputs:
  created_records:
    type: array
    required: true
tools:
  - create_source
  - create_page
  - create_page_version
  - get_page
  - list_pages
---

# Ingest

The caller supplies already retrieved and extracted material. Brain does not fetch or parse
provider documents.

1. Use `list_pages` to select an existing stable Page or decide that a new Page is needed.
2. Create one Source identity with its canonical URI, external identity, status, metadata,
   provenance, policy, and steward.
3. For a new Page, call `create_page` with canonical Markdown and a `derived_from` Source link.
4. For an existing Page, read it, obtain human approval for the proposed content, then call
   `create_page_version` with its current version ID as `expected_current_version_id`.
5. On a conflict, stop and rebase/review. Never merge or overwrite automatically.

Keep claims attributable and preserve meaningful Markdown structure. Do not invent facts.
