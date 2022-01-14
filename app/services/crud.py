from fastapi.encoders import jsonable_encoder
from pymongo.database import Database

from app.models.base import APIBaseModel


async def create_object(model: APIBaseModel, user: str, db: Database) -> dict:
    collection = model.collection_name
    json_model = jsonable_encoder(model)
    new_object = await db[collection].insert_one(json_model)
    created_object = await db[collection].find_one({"_id": new_object.inserted_id})
    return created_object


def update_object(model: APIBaseModel, data: dict) -> APIBaseModel:
    pass
