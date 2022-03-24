import logging

from motor.motor_asyncio import AsyncIOMotorClient
from umongo.document import DocumentImplementation
from umongo.frameworks import MotorAsyncIOInstance

from app.config import get_settings
from app.helpers.connection import conn

logger = logging.getLogger(__name__)

instance = MotorAsyncIOInstance()


async def connect_to_mongo():
    settings = get_settings()
    conn.client = AsyncIOMotorClient(settings.mongodb_url)
    conn.database = conn.client[settings.mongodb_db]
    instance.set_db(conn.database)


async def override_connect_to_mongo():
    settings = get_settings()
    conn.client = AsyncIOMotorClient(settings.mongodb_url)
    conn.database = conn.client[settings.mongodb_test_db]
    instance.set_db(conn.database)


async def close_mongo_connection():
    conn.client.close()


async def create_all_indexes():
    index_names = []
    for name, doc in instance._doc_lookup.items():  # type: str, DocumentImplementation
        indexes = getattr(doc.Meta, "indexes", [])
        for index in indexes:
            result = await doc.collection.create_index(index)
            index_names.append(f"{name}.{result}")

    logger.debug(f"current indexes: {index_names}")
