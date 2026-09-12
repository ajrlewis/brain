from uuid import UUID

from pydantic import BaseModel


class AuthContextResponse(BaseModel):
    organization_id: UUID
    principal_id: UUID
    group_ids: tuple[UUID, ...]
