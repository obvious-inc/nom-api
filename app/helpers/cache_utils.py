from redis.asyncio.client import Redis

from app.config import get_settings
from app.helpers.redis_conn import redis_connection


async def connect_to_redis(db=None):
    settings = get_settings()
    redis = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=db or settings.redis_db,
        auto_close_connection_pool=True,
        decode_responses=True,
    )
    redis_connection.client = redis


async def connect_to_redis_testing():
    return await connect_to_redis(db=1)


async def close_redis_connection():
    await redis_connection.client.close()
