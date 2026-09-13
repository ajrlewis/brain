from brain_ai import EmbeddingProvider, SyntheticEmbeddingProvider, validate_embeddings
from brain_auth import AuthContext, AuthorizationDenied
from brain_core.settings import Settings
from brain_db import (
    AsyncSessionFactory,
    KnowledgeRepository,
    async_session_scope,
    create_async_engine,
    create_async_session_factory,
)
from brain_schemas import SearchRequest, SearchResponse, SearchResult
from brain_search import SearchRepository


class SearchService:
    """Bounded authorization-safe search shared by every transport."""

    def __init__(
        self,
        session_factory: AsyncSessionFactory,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.embedding_provider = embedding_provider or SyntheticEmbeddingProvider()

    async def search(self, context: AuthContext, request: SearchRequest) -> SearchResponse:
        async with async_session_scope(self.session_factory) as session:
            if not await KnowledgeRepository(session).context_is_valid(
                context.organization_id, context.principal_id, context.group_ids
            ):
                raise AuthorizationDenied("The caller's authorization context is not valid")
            vectors = validate_embeddings(await self.embedding_provider.embed([request.query]), 1)
            candidates = await SearchRepository(session).candidates(
                organization_id=context.organization_id,
                group_ids=context.group_ids,
                query=request.query,
                embedding=vectors[0],
                limit=request.limit,
            )
            return SearchResponse(
                query=request.query,
                results=[
                    SearchResult(
                        page_id=item.page_id,
                        page_version_id=item.page_version_id,
                        chunk_id=item.chunk_id,
                        chunk_position=item.chunk_position,
                        title=item.title,
                        path=item.path,
                        heading_path=list(item.heading_path),
                        snippet=_snippet(item.content),
                        score=item.score,
                        lexical_score=item.lexical_score,
                        semantic_score=item.semantic_score,
                    )
                    for item in candidates
                ],
            )


def _snippet(content: str, limit: int = 280) -> str:
    compact = " ".join(content.split())
    return compact if len(compact) <= limit else compact[: limit - 1].rstrip() + "…"


def create_search_service(settings: Settings) -> SearchService:
    engine = create_async_engine(settings)
    return SearchService(create_async_session_factory(engine))
