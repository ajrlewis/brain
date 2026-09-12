from brain_auth import AuthContext, LocalBearerAuthenticator
from brain_core.settings import Settings
from brain_schemas import AuthContextResponse


class IdentityService:
    """Expose the authenticated identity without transport-specific behavior."""

    def describe(self, context: AuthContext) -> AuthContextResponse:
        return AuthContextResponse(
            organization_id=context.organization_id,
            principal_id=context.principal_id,
            group_ids=tuple(sorted(context.group_ids, key=str)),
        )


def create_local_authenticator(settings: Settings) -> LocalBearerAuthenticator:
    configured_token = settings.local_bearer_token
    return LocalBearerAuthenticator(
        token=configured_token.get_secret_value() if configured_token is not None else None,
        context=AuthContext(
            organization_id=settings.local_organization_id,
            principal_id=settings.local_principal_id,
            group_ids=frozenset(settings.local_group_ids),
        ),
    )
