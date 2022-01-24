from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class Connection:
    client: AsyncIOMotorClient = None
    database: AsyncIOMotorDatabase = None


conn = Connection()


async def get_client() -> AsyncIOMotorClient:
    return conn.client


async def get_db() -> AsyncIOMotorDatabase:
    return conn.database
