"""Provider-neutral embedding boundary with a deterministic local implementation."""

from collections.abc import Sequence
from hashlib import sha256
from math import isfinite, sqrt
from typing import Protocol, cast

EMBEDDING_DIMENSIONS = 8


class EmbeddingError(ValueError):
    """Raised when an embedding provider returns an unusable vector."""


class EmbeddingProvider(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class SyntheticEmbeddingProvider:
    """Deterministic local embedding based on hashed word features."""

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return self.embed_sync(texts)

    def embed_sync(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    @staticmethod
    def _embed_one(text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        for token in text.casefold().split():
            digest = sha256(token.strip(".,:;!?()[]{}#`").encode()).digest()
            vector[digest[0] % EMBEDDING_DIMENSIONS] += 1.0 if digest[1] & 1 else -1.0
        norm = sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector


def validate_embeddings(vectors: Sequence[Sequence[float]], expected: int) -> list[list[float]]:
    if len(vectors) != expected:
        raise EmbeddingError("Embedding provider returned the wrong number of vectors")
    raw_vectors = cast(Sequence[Sequence[object]], vectors)
    if any(len(vector) != EMBEDDING_DIMENSIONS for vector in raw_vectors):
        raise EmbeddingError("Embedding provider returned a malformed vector")
    if any(not isinstance(value, (int, float)) for vector in raw_vectors for value in vector):
        raise EmbeddingError("Embedding provider returned a malformed vector")
    result = [[float(cast(float | int, value)) for value in vector] for vector in raw_vectors]
    if any(not isfinite(value) for vector in result for value in vector):
        raise EmbeddingError("Embedding provider returned a malformed vector")
    return result


__all__ = [
    "EMBEDDING_DIMENSIONS",
    "EmbeddingError",
    "EmbeddingProvider",
    "SyntheticEmbeddingProvider",
    "validate_embeddings",
]
