---
name: update
description: Publish a human-approved immutable Page version without losing concurrent work.
inputs:
  page_id:
    type: string
    required: true
  content_markdown:
    type: string
    required: true
  expected_current_version_id:
    type: string
    required: true
  approved:
    type: boolean
    required: true
outputs:
  page:
    type: object
    required: true
tools:
  - get_page
  - create_page_version
---

# Update

Read the Page and prepare a complete replacement Markdown document based on its current
version. Present the content and provenance changes for human confirmation. Do not write
unless `approved` is true.

Immediately before writing, re-read the Page. Call `create_page_version` only when its
current version still equals `expected_current_version_id`. A conflict invalidates the prior
approval: stop, rebase the proposal on the new current version, and request approval again.
Never semantic-merge concurrent edits automatically. Immutable earlier versions remain
history.
