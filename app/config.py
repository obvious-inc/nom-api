from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    testing: bool = True
    profiling: bool = False

    mongodb_url: str = "localhost:27017"
    mongodb_db: str = "newshades"

    jwt_secret_key: str
    jwt_expire_minutes: Optional[int] = 60

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
