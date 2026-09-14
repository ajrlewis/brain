from uuid import UUID

import pytest

from brain_auth import (
    AuthContext,
    AuthenticationError,
    AuthorizationDenied,
    LocalBearerAuthenticator,
    require_access,
)
from brain_core import IdentityService

ORGANIZATION_ID = UUID("10000000-0000-0000-0000-000000000001")
PRINCIPAL_ID = UUID("20000000-0000-0000-0000-000000000001")
GROUP_ID = UUID("30000000-0000-0000-0000-000000000001")


def test_local_bearer_authenticator_returns_configured_context() -> None:
    context = AuthContext(ORGANIZATION_ID, PRINCIPAL_ID, frozenset({GROUP_ID}))
    authenticator = LocalBearerAuthenticator(token="local-secret", context=context)

    assert authenticator.authenticate("Bearer local-secret") == context


@pytest.mark.parametrize(
    "authorization", [None, "", "Basic local-secret", "Bearer wrong", "Bearer café"]
)
def test_local_bearer_authenticator_denies_invalid_credentials(
    authorization: str | None,
) -> None:
    authenticator = LocalBearerAuthenticator(
        token="local-secret",
        context=AuthContext(ORGANIZATION_ID, PRINCIPAL_ID, frozenset()),
    )

    with pytest.raises(AuthenticationError, match="bearer credentials"):
        authenticator.authenticate(authorization)


def test_identity_service_returns_a_stable_group_order() -> None:
    other_group_id = UUID("30000000-0000-0000-0000-000000000002")
    context = AuthContext(
        ORGANIZATION_ID,
        PRINCIPAL_ID,
        frozenset({other_group_id, GROUP_ID}),
    )

    result = IdentityService().describe(context)

    assert result.group_ids == (GROUP_ID, other_group_id)


def test_unrestricted_policy_allows_same_organization() -> None:
    context = AuthContext(ORGANIZATION_ID, PRINCIPAL_ID, frozenset())

    require_access(context, organization_id=ORGANIZATION_ID, permitted_group_ids=())


def test_restricted_policy_allows_any_matching_group() -> None:
    context = AuthContext(ORGANIZATION_ID, PRINCIPAL_ID, frozenset({GROUP_ID}))

    require_access(
        context,
        organization_id=ORGANIZATION_ID,
        permitted_group_ids=(UUID("30000000-0000-0000-0000-000000000002"), GROUP_ID),
    )


@pytest.mark.parametrize(
    ("organization_id", "permitted_group_ids"),
    [
        (UUID("10000000-0000-0000-0000-000000000002"), ()),
        (ORGANIZATION_ID, (UUID("30000000-0000-0000-0000-000000000002"),)),
    ],
)
def test_policy_denies_other_tenant_or_missing_group(
    organization_id: UUID,
    permitted_group_ids: tuple[UUID, ...],
) -> None:
    context = AuthContext(ORGANIZATION_ID, PRINCIPAL_ID, frozenset({GROUP_ID}))

    with pytest.raises(AuthorizationDenied, match="cannot access"):
        require_access(
            context,
            organization_id=organization_id,
            permitted_group_ids=permitted_group_ids,
        )
