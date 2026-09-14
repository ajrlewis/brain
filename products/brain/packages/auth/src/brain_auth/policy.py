from collections.abc import Collection
from uuid import UUID

from brain_auth.context import AuthContext


class AuthorizationDenied(Exception):
    """Raised when an authenticated caller cannot access a resource."""


def require_access(
    context: AuthContext,
    *,
    organization_id: UUID,
    permitted_group_ids: Collection[UUID],
) -> None:
    """Enforce Brain's same-tenant, any-permitted-group policy semantics."""

    same_organization = context.organization_id == organization_id
    group_allowed = not permitted_group_ids or not context.group_ids.isdisjoint(permitted_group_ids)
    if not same_organization or not group_allowed:
        raise AuthorizationDenied("The caller cannot access this resource")
