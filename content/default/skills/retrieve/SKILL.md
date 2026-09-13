---
name: retrieve
description: Navigate authorized Brain inventory and retrieve governed knowledge.
inputs:
  request:
    type: string
    required: true
outputs:
  pages:
    type: array
    required: true
tools:
  - list_pages
  - get_page
  - get_page_by_path
  - get_source
---

# Retrieve

Use `list_pages` as the authoritative exhaustive inventory. Resolve a known stable path with
`get_page_by_path`, or read a selected identity with `get_page`. Read visible Source details
only when the answer needs provenance. Treat omitted records as unavailable; never infer
unauthorized titles, paths, content, or provenance.

Return the smallest set of relevant Pages and cite their stable identities and visible
Sources. A curated home Page is an entry point, not a replacement for inventory.
