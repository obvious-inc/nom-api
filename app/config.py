from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    testing: bool = True
    mongodb_url: str = ""
    mongodb_db: str = ""

    jwt_secret_key: str
    jwt_expire_minutes: int

    web3_provider_url_ws: Optional[str]

    pusher_app_id: Optional[str]
    pusher_key: Optional[str]
    pusher_secret: Optional[str]
    pusher_cluster: Optional[str]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
