import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from starlette.requests import Request

from app.helpers.database import get_db
from app.helpers.jwt import decode_jwt_token
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

    request.state.user_id = user_id
    request.state.auth_type = "bearer"

    return user
