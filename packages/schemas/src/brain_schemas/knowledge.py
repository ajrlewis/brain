from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=63)]


def preserve_nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("String must not be blank")
    return value


Markdown = Annotated[str, AfterValidator(preserve_nonblank)]


class FolderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: Slug
    name: NonBlank
    access_policy_id: UUID
    steward_id: UUID
    parent_id: UUID | None = None
    description: str | None = None
    position: int = 0


class FolderResponse(BaseModel):
    id: UUID
    organization_id: UUID
    parent_id: UUID | None
    kind: str
    slug: str
    name: str
    description: str | None
    access_policy_id: UUID
    position: int
    steward_id: UUID
    created_at: datetime
    updated_at: datetime


class SourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: NonBlank
    title: NonBlank
    status: NonBlank
    access_policy_id: UUID
    steward_id: UUID
    canonical_uri: str | None = None
    external_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    provenance: dict[str, object] = Field(default_factory=dict)


class SourceResponse(BaseModel):
    id: UUID
    organization_id: UUID
    source_type: str
    title: str
    canonical_uri: str | None
    external_id: str | None
    status: str
    access_policy_id: UUID
    steward_id: UUID
    metadata: dict[str, object]
    provenance: dict[str, object]
    created_at: datetime
    updated_at: datetime


class SourceInventoryItem(BaseModel):
    id: UUID
    title: str
    source_type: str
    status: str
    canonical_uri: str | None
    updated_at: datetime


class ProvenanceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: UUID
    relationship: NonBlank
    metadata: dict[str, object] = Field(default_factory=dict)


class ProvenanceResponse(BaseModel):
    source: SourceResponse
    relationship: str
    metadata: dict[str, object]


class PageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: Slug
    title: NonBlank
    content_markdown: Markdown
    access_policy_id: UUID
    steward_id: UUID
    folder_id: UUID | None = None
    position: int = 0
    sources: list[ProvenanceInput] = Field(default_factory=lambda: list[ProvenanceInput]())


class PageVersionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_current_version_id: UUID
    content_markdown: Markdown
    sources: list[ProvenanceInput] = Field(default_factory=lambda: list[ProvenanceInput]())


class PageVersionResponse(BaseModel):
    id: UUID
    page_id: UUID
    version: int
    content_markdown: str
    content_hash: str
    created_by_id: UUID
    created_at: datetime
    provenance: list[ProvenanceResponse]


class PageResponse(BaseModel):
    id: UUID
    organization_id: UUID
    folder_id: UUID | None
    slug: str
    title: str
    access_policy_id: UUID
    position: int
    steward_id: UUID
    created_at: datetime
    updated_at: datetime
    current_version: PageVersionResponse
    versions: list[PageVersionResponse]


class PageInventoryItem(BaseModel):
    id: UUID
    slug: str
    title: str
    path: str
    current_version_id: UUID
    content_hash: str


class SkillCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: Slug
    name: NonBlank
    content_markdown: Markdown
    access_policy_id: UUID
    steward_id: UUID
    folder_id: UUID | None = None
    position: int = 0


class SkillVersionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_current_version_id: UUID
    content_markdown: Markdown


class SkillVersionResponse(BaseModel):
    id: UUID
    skill_id: UUID
    version: int
    content_markdown: str
    content_hash: str
    created_by_id: UUID
    created_at: datetime


class SkillResponse(BaseModel):
    id: UUID
    organization_id: UUID
    folder_id: UUID | None
    slug: str
    name: str
    access_policy_id: UUID
    position: int
    steward_id: UUID
    created_at: datetime
    updated_at: datetime
    current_version: SkillVersionResponse
    versions: list[SkillVersionResponse]


class SkillInventoryItem(BaseModel):
    id: UUID
    slug: str
    name: str
    current_version_id: UUID
    content_hash: str
