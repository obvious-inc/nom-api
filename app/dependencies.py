import logging
from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sentry_sdk import set_user
from starlette.requests import Request

from app.helpers.cache_utils import cache
from app.helpers.jwt import decode_jwt_token
from app.services.users import get_user_by_id

oauth2_scheme = HTTPBearer()

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
