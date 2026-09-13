import { z } from "zod";

export const authorization = z.union([z.string(), z.null()]).optional();
export const AuthContextResponse = z
  .object({
    group_ids: z.array(z.string().uuid()),
    organization_id: z.string().uuid(),
    principal_id: z.string().uuid(),
  })
  .passthrough();
export const ValidationError = z
  .object({
    ctx: z.object({}).partial().passthrough().optional(),
    input: z.unknown().optional(),
    loc: z.array(z.union([z.string(), z.number()])),
    msg: z.string(),
    type: z.string(),
  })
  .passthrough();
export const HTTPValidationError = z
  .object({ detail: z.array(ValidationError) })
  .partial()
  .passthrough();
export const FolderCreate = z.object({
  access_policy_id: z.string().uuid(),
  description: z.union([z.string(), z.null()]).optional(),
  name: z.string().min(1),
  parent_id: z.union([z.string(), z.null()]).optional(),
  position: z.number().int().optional().default(0),
  slug: z
    .string()
    .max(63)
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
  steward_id: z.string().uuid(),
});
export const FolderResponse = z
  .object({
    access_policy_id: z.string().uuid(),
    created_at: z.string().datetime({ offset: true }),
    description: z.union([z.string(), z.null()]),
    id: z.string().uuid(),
    kind: z.string(),
    name: z.string(),
    organization_id: z.string().uuid(),
    parent_id: z.union([z.string(), z.null()]),
    position: z.number().int(),
    slug: z.string(),
    steward_id: z.string().uuid(),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
export const HealthResponse = z
  .object({
    environment: z.string(),
    service: z.string(),
    status: z.string().optional().default("ok"),
  })
  .passthrough();
export const PageInventoryItem = z
  .object({
    content_hash: z.string(),
    current_version_id: z.string().uuid(),
    id: z.string().uuid(),
    path: z.string(),
    slug: z.string(),
    title: z.string(),
  })
  .passthrough();
export const ProvenanceInput = z.object({
  metadata: z.object({}).partial().passthrough().optional(),
  relationship: z.string().min(1),
  source_id: z.string().uuid(),
});
export const PageCreate = z.object({
  access_policy_id: z.string().uuid(),
  content_markdown: z.string(),
  folder_id: z.union([z.string(), z.null()]).optional(),
  position: z.number().int().optional().default(0),
  slug: z
    .string()
    .max(63)
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
  sources: z.array(ProvenanceInput).optional(),
  steward_id: z.string().uuid(),
  title: z.string().min(1),
});
export const SourceResponse = z
  .object({
    access_policy_id: z.string().uuid(),
    canonical_uri: z.union([z.string(), z.null()]),
    created_at: z.string().datetime({ offset: true }),
    external_id: z.union([z.string(), z.null()]),
    id: z.string().uuid(),
    metadata: z.object({}).partial().passthrough(),
    organization_id: z.string().uuid(),
    provenance: z.object({}).partial().passthrough(),
    source_type: z.string(),
    status: z.string(),
    steward_id: z.string().uuid(),
    title: z.string(),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
export const ProvenanceResponse = z
  .object({
    metadata: z.object({}).partial().passthrough(),
    relationship: z.string(),
    source: SourceResponse,
  })
  .passthrough();
export const PageVersionResponse = z
  .object({
    content_hash: z.string(),
    content_markdown: z.string(),
    created_at: z.string().datetime({ offset: true }),
    created_by_id: z.string().uuid(),
    id: z.string().uuid(),
    page_id: z.string().uuid(),
    provenance: z.array(ProvenanceResponse),
    version: z.number().int(),
  })
  .passthrough();
export const PageResponse = z
  .object({
    access_policy_id: z.string().uuid(),
    created_at: z.string().datetime({ offset: true }),
    current_version: PageVersionResponse,
    folder_id: z.union([z.string(), z.null()]),
    id: z.string().uuid(),
    organization_id: z.string().uuid(),
    position: z.number().int(),
    slug: z.string(),
    steward_id: z.string().uuid(),
    title: z.string(),
    updated_at: z.string().datetime({ offset: true }),
    versions: z.array(PageVersionResponse),
  })
  .passthrough();
export const PageVersionCreate = z.object({
  content_markdown: z.string(),
  expected_current_version_id: z.string().uuid(),
  sources: z.array(ProvenanceInput).optional(),
});
export const SearchRequest = z.object({
  limit: z.number().int().gte(1).lte(50).optional().default(10),
  query: z.string().min(1).max(500),
});
export const SearchResult = z
  .object({
    chunk_id: z.string().uuid(),
    chunk_position: z.number().int(),
    heading_path: z.array(z.string()),
    lexical_score: z.number(),
    page_id: z.string().uuid(),
    page_version_id: z.string().uuid(),
    path: z.string(),
    score: z.number(),
    semantic_score: z.number(),
    snippet: z.string(),
    title: z.string(),
  })
  .passthrough();
export const SearchResponse = z
  .object({ query: z.string(), results: z.array(SearchResult) })
  .passthrough();
export const SkillInventoryItem = z
  .object({
    content_hash: z.string(),
    current_version_id: z.string().uuid(),
    id: z.string().uuid(),
    name: z.string(),
    slug: z.string(),
  })
  .passthrough();
export const SkillCreate = z.object({
  access_policy_id: z.string().uuid(),
  content_markdown: z.string(),
  folder_id: z.union([z.string(), z.null()]).optional(),
  name: z.string().min(1),
  position: z.number().int().optional().default(0),
  slug: z
    .string()
    .max(63)
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
  steward_id: z.string().uuid(),
});
export const SkillVersionResponse = z
  .object({
    content_hash: z.string(),
    content_markdown: z.string(),
    created_at: z.string().datetime({ offset: true }),
    created_by_id: z.string().uuid(),
    id: z.string().uuid(),
    skill_id: z.string().uuid(),
    version: z.number().int(),
  })
  .passthrough();
export const SkillResponse = z
  .object({
    access_policy_id: z.string().uuid(),
    created_at: z.string().datetime({ offset: true }),
    current_version: SkillVersionResponse,
    folder_id: z.union([z.string(), z.null()]),
    id: z.string().uuid(),
    name: z.string(),
    organization_id: z.string().uuid(),
    position: z.number().int(),
    slug: z.string(),
    steward_id: z.string().uuid(),
    updated_at: z.string().datetime({ offset: true }),
    versions: z.array(SkillVersionResponse),
  })
  .passthrough();
export const version = z.union([z.number(), z.null()]).optional();
export const SkillVersionCreate = z.object({
  content_markdown: z.string(),
  expected_current_version_id: z.string().uuid(),
});
export const SourceInventoryItem = z
  .object({
    canonical_uri: z.union([z.string(), z.null()]),
    id: z.string().uuid(),
    source_type: z.string(),
    status: z.string(),
    title: z.string(),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
export const SourceCreate = z.object({
  access_policy_id: z.string().uuid(),
  canonical_uri: z.union([z.string(), z.null()]).optional(),
  external_id: z.union([z.string(), z.null()]).optional(),
  metadata: z.object({}).partial().passthrough().optional(),
  provenance: z.object({}).partial().passthrough().optional(),
  source_type: z.string().min(1),
  status: z.string().min(1),
  steward_id: z.string().uuid(),
  title: z.string().min(1),
});
