from datetime import datetime, timedelta
from typing import Optional

from jose import jwt

from app.config import get_settings

ALGORITHM = "HS256"


def generate_jwt_token(data: dict, expires_delta: Optional[timedelta] = None):
    settings = get_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_jwt_token(token: str):
    settings = get_settings()
    data = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    return data
