import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sentry_sdk import set_user
from starlette.requests import Request

from app.helpers.connection import get_db
from app.helpers.jwt import decode_jwt_token
from app.models.auth import RefreshToken
from app.services.crud import get_items
from app.services.users import get_user_by_id

oauth2_scheme = HTTPBearer()


logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme), db=Depends(get_db)
):
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

    # TODO: use cache for this
    refresh_tokens = await get_items(filters={"user": user.pk}, result_obj=RefreshToken, current_user=user)
    if len(refresh_tokens) == 0:
        logger.warning("Refresh tokens have all been revoked. [user_id=%s]", user_id)
        raise credentials_exception

    request.state.user_id = user_id
    request.state.auth_type = "bearer"

    set_user({"id": user_id})

    return user
