from typing import Any, List

from redis.asyncio.client import Redis

from app.config import get_settings


class Cache:
    client: Redis = None


cache = Cache()


async def connect_to_redis(db=None):
    settings = get_settings()
    redis = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=db or settings.redis_db,
        username=settings.redis_username,
        password=settings.redis_password,
        auto_close_connection_pool=True,
        decode_responses=True,
    )
    await redis.ping()
    cache.client = redis


async def connect_to_redis_testing():
    return await connect_to_redis(db=1)


async def close_redis_connection():
    await cache.client.close()


async def convert_redis_list_to_dict(data: List[Any]):
    data_iter = iter(data)
    return dict(zip(data_iter, data_iter))
