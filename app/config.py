from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    testing: bool = True
    mongodb_url: str = ""
    mongodb_db: str = ""

    jwt_secret_key: str
    jwt_expire_minutes: int

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
