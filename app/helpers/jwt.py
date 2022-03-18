from datetime import datetime, timedelta
from typing import Optional

from jose import jwt

from app.config import get_settings

ALGORITHM = "HS256"


def generate_jwt_token(data: dict, expires_delta: Optional[timedelta] = None, token_type: Optional[str] = "access"):
    settings = get_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow()
        if token_type == "access":
            expire += timedelta(minutes=settings.jwt_access_token_expire_minutes)
        elif token_type == "refresh":
            expire += timedelta(minutes=settings.jwt_refresh_token_expire_minutes)
        else:
            raise ValueError(f"unexpected token type: {token_type}")

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_jwt_token(token: str, options: Optional[dict] = None):
    settings = get_settings()
    data = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM], options=options)
    return data
