---
name: index
description: Route a Brain knowledge task to the focused current Skill that governs it.
inputs:
  purpose:
    type: string
    required: true
outputs:
  skill_slug:
    type: string
    required: true
  required_inputs:
    type: object
    required: true
tools:
  - get_skill_by_slug
  - list_skills
routes:
  ingest:
    purpose: Add extracted external knowledge with provenance.
    inputs: [source, pages]
    tools: [create_source, create_page, create_page_version, get_page, list_pages]
  retrieve:
    purpose: Navigate and read governed knowledge.
    inputs: [request]
    tools: [list_pages, get_page, get_page_by_path, get_source]
  update:
    purpose: Propose and publish a reviewed correction.
    inputs: [page_id, content_markdown, expected_current_version_id, approved]
    tools: [get_page, create_page_version]
  lint:
    purpose: Audit Skills and knowledge structure.
    inputs: [scope]
    tools: [list_skills, get_skill_by_slug, list_pages, get_page, get_page_by_path, list_sources, get_source]
---

# Skill index

Retrieve the selected Skill by stable slug and follow that current document. This index is
only a routing contract; it does not duplicate the routed instructions.

| Purpose | Skill slug | Required inputs | Brain tools |
| --- | --- | --- | --- |
| Add extracted external knowledge with provenance | `ingest` | `source`, `pages` | `create_source`, `create_page`, `create_page_version`, `get_page`, `list_pages` |
| Navigate and read governed knowledge | `retrieve` | `request` | `list_pages`, `get_page`, `get_page_by_path`, `get_source` |
| Propose and publish a reviewed correction | `update` | `page_id`, `content_markdown`, `expected_current_version_id`, `approved` | `get_page`, `create_page_version` |
| Audit Skills and knowledge structure | `lint` | `scope` | `list_skills`, `get_skill_by_slug`, `list_pages`, `get_page`, `get_page_by_path`, `list_sources`, `get_source` |

If no route matches, return that the capability is unavailable. Do not invent a tool or
silently substitute a write workflow.
