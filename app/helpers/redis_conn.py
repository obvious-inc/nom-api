from redis.asyncio.client import Redis


class RedisConnection:
    client: Redis = None


redis_connection = RedisConnection()


async def get_redis() -> Redis:
    return redis_connection.client
