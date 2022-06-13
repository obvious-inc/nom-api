import logging
from typing import List, Optional, Union, cast

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sentry_sdk import set_user
from starlette.requests import Request

from app.helpers.cache_utils import cache
from app.helpers.jwt import decode_jwt_token
from app.helpers.permissions import check_request_permissions
from app.models.user import User
from app.services.users import get_user_by_id

oauth2_scheme = HTTPBearer()
oauth2_no_error_scheme = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)


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

    user = await get_user_by_id(user_id=user_id)
    if not user:
        logger.warning("User in JWT token not found. [user_id=%s]", user_id)
        raise credentials_exception

    if not await cache.client.smembers(f"refresh_tokens:{str(user.pk)}"):
        logger.warning("Refresh tokens have all been revoked. [user_id=%s]", user_id)
        raise credentials_exception

    request.state.user_id = user_id
    request.state.auth_type = "bearer"

    set_user({"id": user_id})

    return user


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


class PermissionsChecker:
    def __init__(self, needs_user: bool = True, permissions: List[str] = None):
        self.needs_user = needs_user
        self.permissions = permissions

    async def __call__(
        self, request: Request, user_or_exception: Union[User, Exception, None] = Depends(get_current_user_non_error)
    ):
        if isinstance(user_or_exception, Exception):
            raise user_or_exception

        if self.needs_user and user_or_exception is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if self.permissions:
            user = cast(User, user_or_exception)
            await check_request_permissions(request=request, current_user=user, permissions=self.permissions)


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
