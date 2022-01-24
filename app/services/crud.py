import logging
from typing import Optional, Type

from bson import ObjectId

from app.models.base import APIDocument
from app.models.user import User
from app.schemas.base import APIBaseCreateSchema

logger = logging.getLogger(__name__)


async def create_item(
    item: APIBaseCreateSchema, result_obj: Type[APIDocument], current_user: User, user_field: Optional[str] = "user"
) -> APIDocument:
    db_object = result_obj(**item.dict())
    if user_field:
        db_object[user_field] = current_user
    await db_object.commit()
    logger.info("Object created. [object_type=%s, object_id=%s]", result_obj.__name__, str(db_object.id))
    return db_object


async def get_item_by_id(id_: str, result_obj: Type[APIDocument], current_user: User) -> APIDocument:
    item = await result_obj.find_one({"_id": ObjectId(id_)})
    return item


async def get_items(
    filters: dict, result_obj: Type[APIDocument], current_user: User, size: Optional[int] = None
) -> [APIDocument]:
    # TODO: add paging default size to settings
    items = await result_obj.find(filters).sort("created_at", -1).to_list(length=size)
    return items


async def get_item(filters: dict, result_obj: Type[APIDocument], current_user: User) -> APIDocument:
    item = await result_obj.find_one(filters)
    return item


async def update_item(item: APIDocument, data: dict) -> APIDocument:
    item.update(data)
    await item.commit()
    return item


async def delete_item(item: APIDocument) -> APIDocument:
    return await update_item(item, {"deleted": True})
