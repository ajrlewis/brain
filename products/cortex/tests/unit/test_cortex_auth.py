import pytest

from cortex_auth import AuthenticationError, LocalBearerAuthenticator


def test_local_bearer_authenticates_configured_owner() -> None:
    authenticator = LocalBearerAuthenticator(token="synthetic-token", owner_id="owner-a")

    assert authenticator.authenticate("Bearer synthetic-token").owner_id == "owner-a"


@pytest.mark.parametrize("authorization", [None, "", "Basic synthetic-token", "Bearer wrong"])
def test_local_bearer_rejects_absent_or_invalid_credentials(authorization: str | None) -> None:
    authenticator = LocalBearerAuthenticator(token="synthetic-token", owner_id="owner-a")

    with pytest.raises(AuthenticationError):
        authenticator.authenticate(authorization)
