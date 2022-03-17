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
        delta_expiry = (
            settings.jwt_access_token_expire_minutes
            if token_type == "access"
            else settings.jwt_refresh_token_expire_minutes
        )
        expire = datetime.utcnow() + timedelta(minutes=delta_expiry)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_jwt_token(token: str):
    settings = get_settings()
    data = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    return data
