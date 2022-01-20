from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.database import Database
from umongo.frameworks import MotorAsyncIOInstance

from app.config import get_settings

instance = MotorAsyncIOInstance()


async def get_client() -> AsyncIOMotorClient:
    settings = get_settings()
    return AsyncIOMotorClient(settings.mongodb_url)


async def get_db() -> Database:
    settings = get_settings()
    client = await get_client()
    db = client[settings.mongodb_db]
    instance.set_db(db)
    return db


async def override_get_db():
    settings = get_settings()
    settings.mongodb_db = "newshades-test"
    client = await get_client()
    db = client[settings.mongodb_db]
    instance.set_db(db)
    return db
