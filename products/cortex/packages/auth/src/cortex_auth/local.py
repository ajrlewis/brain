from dataclasses import dataclass
from hmac import compare_digest


class AuthenticationError(Exception):
    """Raised when local bearer credentials are absent or invalid."""


@dataclass(frozen=True, slots=True)
class CallerIdentity:
    owner_id: str


class LocalBearerAuthenticator:
    """Authenticate one configured local-development caller."""

    def __init__(self, *, token: str, owner_id: str) -> None:
        self._token = token
        self._identity = CallerIdentity(owner_id=owner_id)

    def authenticate(self, authorization: str | None) -> CallerIdentity:
        scheme, _, credentials = (authorization or "").partition(" ")
        if (
            scheme.lower() != "bearer"
            or not credentials
            or not compare_digest(credentials.encode(), self._token.encode())
        ):
            raise AuthenticationError
        return self._identity
