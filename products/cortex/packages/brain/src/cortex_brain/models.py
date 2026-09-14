from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CortexBrainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BrainHealth(CortexBrainModel):
    status: Literal["ok"]
    service: str
    environment: str


class BrainIdentityContext(CortexBrainModel):
    organization_id: UUID
    principal_id: UUID
    group_ids: tuple[UUID, ...]
