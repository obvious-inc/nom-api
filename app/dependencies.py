import logging
from typing import List, Optional, Union, cast

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials, HTTPBearer
from jose import JWTError
from sentry_sdk import set_user
from starlette.requests import Request

from app.helpers.cache_utils import cache
from app.helpers.jwt import decode_jwt_token
from app.helpers.permissions import check_request_permissions
from app.models.app import App
from app.models.user import User
from app.services.apps import get_app_by_client_id
from app.services.users import get_user_by_id

oauth2_scheme = HTTPBearer()
oauth2_no_error_scheme = HTTPBearer(auto_error=False)
basic_scheme = HTTPBasic()

logger = logging.getLogger(__name__)


async def get_current_client(request: Request, credentials: HTTPBasicCredentials = Depends(basic_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate client credentials",
        headers={"WWW-Authenticate": "Basic"},
    )

    client_id = credentials.username
    client_secret = credentials.password
    app: App = await get_app_by_client_id(client_id)

    request.state.auth_type = "basic"

    if not app:
        logger.warning("Client not found. [client_id=%s]", client_id)
        raise credentials_exception

    if app.client_secret != client_secret:
        logger.warning("Client details don't match. [client_id=%s]", client_id)
        raise credentials_exception

    return app


async def get_current_user(request: Request, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_jwt_token(token.credentials)
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    except Exception:
        logger.exception("Problems decoding JWT. [jwt=%s]", token.credentials)
        raise credentials_exception

    request.state.auth_type = "bearer"

    client_id: str = payload.get("client_id")
    if client_id:
        return None

    user: User = await get_user_by_id(user_id=user_id)
    if not user:
        logger.warning("User in JWT token not found. [user_id=%s]", user_id)
        raise credentials_exception

    if not await cache.client.smembers(f"refresh_tokens:{str(user.pk)}"):
        logger.warning("Refresh tokens have all been revoked. [user_id=%s]", user_id)
        raise credentials_exception

    request.state.user_id = user_id
    request.state.actor_type = "user"
    request.state.auth_source = "wallet"
    set_user({"id": user_id, "type": "user"})
    return user


async def get_current_app(request: Request, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_jwt_token(token.credentials)
        sub: str = payload.get("sub")
        if not sub:
            raise credentials_exception
    except JWTError as e:
        logger.debug(f"jwt error: {e}")
        raise credentials_exception
    except Exception:
        logger.exception("Problems decoding JWT. [jwt=%s]", token.credentials)
        raise credentials_exception

    request.state.auth_type = "bearer"
    client_id: str = payload.get("client_id")
    if not client_id:
        return None

    app: App = await get_app_by_client_id(client_id)
    if str(app.pk) != sub:
        raise credentials_exception

    if not app:
        logger.warning("App in JWT token not found. [app_id=%s]", sub)
        raise credentials_exception

    if not await cache.client.smembers(f"refresh_tokens:{str(app.pk)}"):
        logger.warning("Refresh tokens have all been revoked. [app_id=%s]", sub)
        raise credentials_exception

    request.state.app_id = sub
    request.state.actor_type = "app"
    request.state.auth_source = "oauth2"
    request.state.scopes = payload.get("scopes", [])

    set_user({"id": str(app.pk), "name": app.name, "type": "app", "client_id": client_id})
    return app


async def get_current_user_non_error(
    request: Request, token: HTTPAuthorizationCredentials = Depends(oauth2_no_error_scheme)
):
    if not token:
        return None

    try:
        current_user = await get_current_user(request, token)
        return current_user
    except Exception as e:
        return e


async def get_current_app_non_error(
    request: Request, token: HTTPAuthorizationCredentials = Depends(oauth2_no_error_scheme)
):
    if not token:
        return None

    try:
        current_app = await get_current_app(request, token)
        return current_app
    except Exception as e:
        return e


class PermissionsChecker:
    def __init__(self, needs_bearer: bool = True, permissions: List[str] = None, raise_exception: Exception = None):
        self.needs_bearer = needs_bearer
        self.permissions = permissions
        self.raise_exception = raise_exception

    async def __call__(
        self,
        request: Request,
        user_or_exception: Union[User, Exception, None] = Depends(get_current_user_non_error),
        app_or_exception: Union[App, Exception, None] = Depends(get_current_app_non_error),
    ):
        if isinstance(user_or_exception, Exception):
            raise user_or_exception

        if isinstance(app_or_exception, Exception):
            raise app_or_exception

        if self.needs_bearer and user_or_exception is None and app_or_exception is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if self.permissions:
            user = cast(User, user_or_exception)
            app = cast(App, app_or_exception)

            await check_request_permissions(
                request=request,
                current_user=user,
                current_app=app,
                permissions=self.permissions,
                raise_exception=self.raise_exception,
            )


async def common_parameters(
    before: Optional[str] = None,
    after: Optional[str] = None,
    around: Optional[str] = None,
    limit: int = Query(50, gt=0, le=100),
    sort_by_field: str = "created_at",
    sort_by_direction: int = -1,
    sort: str = None,
):
    present = [v for v in [before, after, around] if v is not None]
    if len(present) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only one of 'before', 'after' and 'around can be present."
        )

    if sort:
        if sort.startswith("-"):
            sort_by_field = sort[1:]
            sort_by_direction = -1
        else:
            sort_by_field = sort
            sort_by_direction = 1

    return {
        "before": before,
        "after": after,
        "around": around,
        "limit": limit,
        "sort_by_field": sort_by_field,
        "sort_by_direction": sort_by_direction,
    }
