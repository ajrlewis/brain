from dataclasses import dataclass
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class SearchCandidate:
    page_id: UUID
    page_version_id: UUID
    chunk_id: UUID
    chunk_position: int
    title: str
    slug: str
    path: str
    heading_path: tuple[str, ...]
    content: str
    lexical_score: float
    semantic_score: float
    score: float


class SearchRepository:
    """PostgreSQL retrieval with authorization inside each candidate CTE."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def candidates(
        self,
        *,
        organization_id: UUID,
        group_ids: frozenset[UUID],
        query: str,
        embedding: list[float],
        limit: int,
    ) -> list[SearchCandidate]:
        candidate_limit = limit * 4
        statement = text("""
            WITH RECURSIVE folder_paths AS (
              SELECT id, organization_id, parent_id, '/' || slug AS path
              FROM folders WHERE parent_id IS NULL AND deleted_at IS NULL
              UNION ALL
              SELECT f.id, f.organization_id, f.parent_id, fp.path || '/' || f.slug
              FROM folders f JOIN folder_paths fp
                ON fp.id = f.parent_id AND fp.organization_id = f.organization_id
              WHERE f.deleted_at IS NULL
            ), authorized AS MATERIALIZED (
              SELECT c.id AS chunk_id, c.page_version_id, c.position, c.heading_path,
                     c.content, c.embedding, p.id AS page_id, p.title, p.slug,
                     COALESCE(fp.path, '') || '/' || p.slug AS path
              FROM chunks c
              JOIN page_versions pv ON pv.id = c.page_version_id
                                      AND pv.organization_id = c.organization_id
              JOIN pages p ON p.id = pv.page_id AND p.organization_id = c.organization_id
              LEFT JOIN folder_paths fp ON fp.id = p.folder_id
                                       AND fp.organization_id = p.organization_id
              WHERE c.organization_id = :organization_id
                AND p.deleted_at IS NULL
                AND p.current_version_id = pv.id
                AND (
                  NOT EXISTS (
                    SELECT 1 FROM access_policy_groups apg
                    WHERE apg.organization_id = p.organization_id
                      AND apg.access_policy_id = p.access_policy_id
                  )
                  OR EXISTS (
                    SELECT 1 FROM access_policy_groups apg
                    WHERE apg.organization_id = p.organization_id
                      AND apg.access_policy_id = p.access_policy_id
                      AND apg.group_id = ANY(:group_ids)
                  )
                )
            ), lexical AS (
              SELECT *, ts_rank_cd(to_tsvector('english', content),
                                    plainto_tsquery('english', :query)) AS lexical_score
              FROM authorized
              WHERE to_tsvector('english', content) @@ plainto_tsquery('english', :query)
              ORDER BY lexical_score DESC, chunk_id
              LIMIT :candidate_limit
            ), semantic AS (
              SELECT *, 1 - (embedding <=> :embedding) AS semantic_score
              FROM authorized
              ORDER BY embedding <=> :embedding, chunk_id
              LIMIT :candidate_limit
            ), combined AS (
              SELECT COALESCE(l.chunk_id, s.chunk_id) AS chunk_id,
                     COALESCE(l.page_version_id, s.page_version_id) AS page_version_id,
                     COALESCE(l.position, s.position) AS position,
                     COALESCE(l.heading_path, s.heading_path) AS heading_path,
                     COALESCE(l.content, s.content) AS content,
                     COALESCE(l.page_id, s.page_id) AS page_id,
                     COALESCE(l.title, s.title) AS title,
                     COALESCE(l.slug, s.slug) AS slug,
                     COALESCE(l.path, s.path) AS path,
                     COALESCE(l.lexical_score, 0) AS lexical_score,
                     COALESCE(s.semantic_score, 0) AS semantic_score
              FROM lexical l FULL OUTER JOIN semantic s USING (chunk_id)
            )
            SELECT *, lexical_score + semantic_score AS score
            FROM combined
            ORDER BY score DESC, page_id, position
            LIMIT :limit
        """).bindparams(bindparam("embedding", type_=Vector(8)))
        rows = (
            await self.session.execute(
                statement,
                {
                    "organization_id": organization_id,
                    "group_ids": list(group_ids),
                    "query": query,
                    "embedding": embedding,
                    "candidate_limit": candidate_limit,
                    "limit": limit,
                },
            )
        ).mappings()
        return [
            SearchCandidate(
                page_id=row["page_id"],
                page_version_id=row["page_version_id"],
                chunk_id=row["chunk_id"],
                chunk_position=row["position"],
                title=row["title"],
                slug=row["slug"],
                path=row["path"],
                heading_path=tuple(row["heading_path"]),
                content=row["content"],
                lexical_score=float(row["lexical_score"]),
                semantic_score=float(row["semantic_score"]),
                score=float(row["score"]),
            )
            for row in rows
        ]
