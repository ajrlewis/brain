from hmac import compare_digest

from brain_auth.context import AuthContext


class AuthenticationError(Exception):
    """Raised when local bearer credentials are absent or invalid."""


class LocalBearerAuthenticator:
    """Authenticate one configured local-development bearer token."""

    def __init__(self, *, token: str | None, context: AuthContext) -> None:
        self._token = token
        self._context = context

    def authenticate(self, authorization: str | None) -> AuthContext:
        scheme, _, credentials = (authorization or "").partition(" ")
        if (
            self._token is None
            or scheme.lower() != "bearer"
            or not credentials
            or not compare_digest(credentials.encode(), self._token.encode())
        ):
            raise AuthenticationError("Valid bearer credentials are required")
        return self._context
