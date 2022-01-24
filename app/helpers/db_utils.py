from motor.motor_asyncio import AsyncIOMotorClient
from umongo.frameworks import MotorAsyncIOInstance

from app.config import get_settings
from app.helpers.connection import conn

instance = MotorAsyncIOInstance()


async def connect_to_mongo():
    settings = get_settings()
    conn.client = AsyncIOMotorClient(settings.mongodb_url)
    conn.database = conn.client[settings.mongodb_db]
    instance.set_db(conn.database)


async def override_connect_to_mongo():
    settings = get_settings()
    conn.client = AsyncIOMotorClient(settings.mongodb_url)
    conn.database = conn.client["newshades-test"]
    instance.set_db(conn.database)


async def close_mongo_connection():
    conn.client.close()
