import json

from redis import asyncio as aioredis

from app.config import get_settings


class RedisConnection:
    client = None


redis_connection = RedisConnection()


async def connect_redis():
    settings = get_settings()
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    redis_connection.client = redis


async def get_redis():
    return redis_connection.client


async def is_cached(prefix: str) -> bool:
    return await redis_connection.client.exists(prefix)


async def cache_get(prefix: str) -> dict:
    if not redis_connection.client:
        return

    return json.loads(await redis_connection.client.get(prefix))


async def cache_set(prefix: str, dict_value: dict):
    if not redis_connection.client:
        return

    await redis_connection.client.set(prefix, json.dumps(dict_value))
