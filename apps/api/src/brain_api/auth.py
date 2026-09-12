from typing import Annotated, cast

from fastapi import Header, HTTPException, Request, status

from brain_auth import AuthContext, AuthenticationError, LocalBearerAuthenticator


def get_authenticator(request: Request) -> LocalBearerAuthenticator:
    return cast(LocalBearerAuthenticator, request.app.state.authenticator)


def get_auth_context(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> AuthContext:
    try:
        return get_authenticator(request).authenticate(authorization)
    except AuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
