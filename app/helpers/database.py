from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.database import Database

from app.config import get_settings


async def get_client() -> AsyncIOMotorClient:
    settings = get_settings()
    return AsyncIOMotorClient(settings.mongodb_url)


async def get_db() -> Database:
    settings = get_settings()
    client = await get_client()
    db = client[settings.mongodb_db]
    return db
