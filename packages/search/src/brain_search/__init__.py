"""Authorized retrieval boundary; implementation is intentionally deferred."""

from brain_search.chunking import ChunkDraft, chunk_markdown
from brain_search.repository import SearchCandidate, SearchRepository

__all__ = ["ChunkDraft", "SearchCandidate", "SearchRepository", "chunk_markdown"]
