from collections.abc import Sequence
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from brain_ai import EmbeddingError, SyntheticEmbeddingProvider
from brain_auth import AuthContext
from brain_core.search import SearchService
from brain_schemas import SearchRequest
from brain_search import SearchCandidate, chunk_markdown

ORG = UUID("10000000-0000-0000-0000-000000000001")
PRINCIPAL = UUID("20000000-0000-0000-0000-000000000001")


def test_markdown_chunking_is_deterministic_and_tracks_heading_paths() -> None:
    markdown = "Intro.\n\n# Alpha\n\nFirst.\n\n## Beta\n\nSecond."

    first = chunk_markdown(markdown, max_characters=20)
    second = chunk_markdown(markdown, max_characters=20)

    assert first == second
    assert [chunk.position for chunk in first] == list(range(len(first)))
    assert [chunk.heading_path for chunk in first] == [(), ("Alpha",), ("Alpha", "Beta")]
    assert all(len(chunk.content_hash) == 64 for chunk in first)


async def test_synthetic_embeddings_are_repeatable_and_query_sensitive() -> None:
    provider = SyntheticEmbeddingProvider()

    vectors = await provider.embed(["alpha beta", "alpha beta", "different"])

    assert vectors[0] == vectors[1]
    assert vectors[0] != vectors[2]


def test_search_request_rejects_empty_queries_and_unbounded_limits() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(query="   ")
    with pytest.raises(ValidationError):
        SearchRequest(query="valid", limit=51)


class BadProvider:
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float("nan")] * 8]


async def test_search_rejects_malformed_provider_embeddings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = AsyncMock()
    repository.context_is_valid.return_value = True

    def context_repository(_session: AsyncSession) -> AsyncMock:
        return repository

    monkeypatch.setattr("brain_core.search.KnowledgeRepository", context_repository)
    service = SearchService(lambda: AsyncMock(spec=AsyncSession), BadProvider())

    with pytest.raises(EmbeddingError, match="malformed"):
        await service.search(
            AuthContext(organization_id=ORG, principal_id=PRINCIPAL, group_ids=frozenset()),
            SearchRequest(query="alpha"),
        )


async def test_search_shapes_bounded_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    context_repository = AsyncMock()
    context_repository.context_is_valid.return_value = True
    candidate = SearchCandidate(
        page_id=uuid4(),
        page_version_id=uuid4(),
        chunk_id=uuid4(),
        chunk_position=0,
        title="Alpha",
        slug="alpha",
        path="/facts/alpha",
        heading_path=("Facts",),
        content="  A safe   authorized snippet.  ",
        lexical_score=0.5,
        semantic_score=0.4,
        score=0.9,
    )
    search_repository = AsyncMock()
    search_repository.candidates.return_value = [candidate]

    def knowledge_factory(_session: AsyncSession) -> AsyncMock:
        return context_repository

    def search_factory(_session: AsyncSession) -> AsyncMock:
        return search_repository

    monkeypatch.setattr("brain_core.search.KnowledgeRepository", knowledge_factory)
    monkeypatch.setattr("brain_core.search.SearchRepository", search_factory)
    service = SearchService(lambda: AsyncMock(spec=AsyncSession))

    response = await service.search(
        AuthContext(organization_id=ORG, principal_id=PRINCIPAL, group_ids=frozenset()),
        SearchRequest(query=" alpha ", limit=3),
    )

    assert response.query == "alpha"
    assert response.results[0].snippet == "A safe authorized snippet."
    search_repository.candidates.assert_awaited_once_with(
        organization_id=ORG,
        group_ids=frozenset(),
        query="alpha",
        embedding=(await SyntheticEmbeddingProvider().embed(["alpha"]))[0],
        limit=3,
    )
