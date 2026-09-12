# Data Model

This document is the contract for Brain's initial identity, access, knowledge, and Skill
model. The migrations implement the identity/access and knowledge tables identified
below; Skill tables are specified for a subsequent vertical slice.

PostgreSQL UUID primary keys are stable public identifiers. Timestamps are timezone-aware.
Tenant-owned uniqueness and foreign keys include `organization_id` so records from two
organizations cannot be linked accidentally. JSON fields use JSONB and must contain JSON
objects unless a field says otherwise.

## Identity and access foundation (implemented)

### Organization

| Field | Contract |
| --- | --- |
| `id` | UUID primary key |
| `slug` | Globally unique, 1-63 lowercase letters/digits separated by single hyphens |
| `name` | Non-blank string, at most 255 characters |
| `created_at`, `updated_at` | Required timestamps |
| `deleted_at` | Nullable soft-deletion timestamp |

An Organization is the tenant root, so it does not point to itself. Physical deletion is
restricted while tenant-owned rows exist.

### Principal

| Field | Contract |
| --- | --- |
| `id` | UUID primary key |
| `organization_id` | Required Organization |
| `kind` | `user`, `service`, or `agent` |
| `external_subject` | Provider-neutral subject, unique within the Organization |
| `display_name` | Non-blank string, at most 255 characters |
| `is_active` | Required boolean, default true |
| timestamps | `created_at`, `updated_at`, nullable `deleted_at` |

Provider-specific profile data and identity-provider administration are outside this
model. A deactivated or soft-deleted Principal cannot authenticate. Physical deletion is
restricted by owned/audit records; GroupMembership links cascade.

### Group and GroupMembership

Group has `id`, required `organization_id`, organization-unique `slug`, non-blank `name`,
nullable `description`, and the standard timestamps. Slugs use the Organization slug
format. GroupMembership has `(organization_id, group_id, principal_id)` as its primary
key and a required `created_at` timestamp. Its composite foreign keys require the Group
and Principal to belong to the same Organization. Deleting either parent deletes the link.

### AccessPolicy and AccessPolicyGroup

AccessPolicy has `id`, required `organization_id`, an organization-unique non-blank
`name`, nullable `description`, and the standard timestamps. AccessPolicyGroup has
`(organization_id, access_policy_id, group_id)` as its primary key. Composite foreign keys
prevent cross-organization policy grants. Deleting a policy or group deletes its link.

An AccessPolicy with no AccessPolicyGroup rows grants organization-wide access. Otherwise
it grants access to members of at least one linked Group. A policy is reusable; it does
not own the records that reference it, and its physical deletion is restricted while in
use.

## Navigation (Page folders implemented)

### Folder

Folder fields are `id`, `organization_id`, nullable `parent_id`, `kind` (`page` or
`skill`), `slug`, `name`, nullable `description`, `access_policy_id`, integer `position`,
`steward_id`, `created_by_id`, `updated_by_id`, `created_at`, `updated_at`, and
`deleted_at`. Sibling `(parent_id, kind, slug)` values are unique within an Organization.
A child must have the same Organization and kind as its parent; cycles are forbidden.
Page folders contain Pages and Skill folders contain Skills. Root folders have no parent.
This first knowledge slice permits only `page` folders; `skill` folders remain deferred.

Folders are soft-deleted. Deletion is rejected while live children or live items remain.
Position is navigation order only and has no retrieval meaning.

## Knowledge (implemented)

### Source

Source fields are `id`, `organization_id`, `source_type`, `title`, nullable
`canonical_uri`, nullable `external_id`, `status`, `access_policy_id`, `metadata` JSONB,
`provenance` JSONB, `created_by_id`, `updated_by_id`, `steward_id`, standard timestamps,
and `deleted_at`. `(source_type, external_id)` is unique within an Organization when
`external_id` is present. Type and status are non-blank strings rather than provider
enums. Metadata may describe a provider without introducing provider-specific tables.

Sources are soft-deleted. Historical PageVersionSource links are retained; normal reads
exclude deleted Sources, including from provenance.

A Source records identity and provenance metadata; it does not store the original binary
document or its extracted body. Cortex supplies extracted Markdown as PageVersion content.

### Page

Page fields are `id`, `organization_id`, nullable `folder_id`, `slug`, `title`, nullable
`current_version_id`, `access_policy_id`, integer `position`, `steward_id`,
`created_by_id`, `updated_by_id`, standard timestamps, and `deleted_at`. Slug is unique
within an Organization. Folder, policy, steward, and audit principals must belong to the
same Organization. A Page may be created without a current version inside a write unit of
work, but public retrieval requires one.

The current-version foreign key must point to a PageVersion owned by that same Page. Page
is a stable identity and contains no Markdown or content hash. Pages are soft-deleted;
versions and provenance are retained.

Page authorization is relational metadata on `Page`, never trusted from YAML frontmatter
inside supplied Markdown. A summary is not a separate canonical field in the initial
model; future derived summaries or snippets inherit the Page policy.

### PageVersion

PageVersion fields are `id`, `page_id`, positive integer `version`,
`content_markdown`, lowercase SHA-256 `content_hash`, `created_by_id`, and `created_at`.
Version and content hash are each unique per Page. Markdown is non-blank and exists only
on the immutable version. Updates and deletes are rejected during normal application
operation; a new version is created instead. Moving `Page.current_version_id` provides
rollback without changing a version.

### PageVersionSource

PageVersionSource fields are `organization_id`, `page_version_id`, `source_id`,
`relationship`, and `metadata` JSONB. `(page_version_id, source_id, relationship)` is the
primary key. Composite references ensure the PageVersion's Page and Source are in the
same Organization. Relationship is a non-blank vocabulary such as `derived_from` or
`corroborated_by`. Deleting canonical versions or Sources is restricted; links are part
of retained provenance.

## Skills (specified, not yet migrated)

### Skill

Skill fields are `id`, `organization_id`, nullable `folder_id`, `slug`, `name`, nullable
`current_version_id`, `access_policy_id`, integer `position`, `steward_id`,
`created_by_id`, `updated_by_id`, standard timestamps, and `deleted_at`. Slug is unique
within an Organization. Folder, policy, steward, and audit identities are same-tenant.
Skill is stable identity and contains no instructions or content hash.

### SkillVersion

SkillVersion fields are `id`, `skill_id`, positive integer `version`,
`content_markdown`, lowercase SHA-256 `content_hash`, `created_by_id`, and `created_at`.
Version and content hash are unique per Skill. `content_markdown` is the complete immutable
Markdown document, including validated YAML frontmatter. `Skill.current_version_id` must
point to a version of that same Skill. The creation and deletion rules match PageVersion.

## Canonical and derived data boundary

Organizations, navigation, Sources, Pages and immutable PageVersions, provenance links,
Skills, and immutable SkillVersions are canonical. Only PageVersion and SkillVersion may
store their respective Markdown content.

Chunks, full-text indexes, and embeddings are derived exclusively from PageVersion
content. Every Chunk identifies its PageVersion, ordinal position, text, heading path,
token count, and content hash. Every embedding records provider, model, dimensions, and
the Chunk it represents. Derived rows have no independent policy or stewardship and may
be deleted and rebuilt without changing canonical records or current-version pointers.
Authorization is inherited from the owning Page at query time.
