from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

SearchQuery = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: SearchQuery
    limit: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    page_id: UUID
    page_version_id: UUID
    chunk_id: UUID
    chunk_position: int
    title: str
    path: str
    heading_path: list[str]
    snippet: str
    score: float
    lexical_score: float
    semantic_score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
