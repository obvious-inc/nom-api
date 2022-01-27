import logging
from typing import Optional, Type, Union

from bson import ObjectId
from umongo import Reference

from app.models.base import APIDocument
from app.models.user import User
from app.schemas.base import APIBaseCreateSchema

logger = logging.getLogger(__name__)


async def create_item(
    item: APIBaseCreateSchema,
    result_obj: Type[APIDocument],
    current_user: Union[User, APIDocument],
    user_field: Optional[str] = "user",
) -> APIDocument:
    db_object = result_obj(**item.dict())
    if user_field:
        db_object[user_field] = current_user
    await db_object.commit()
    logger.info("Object created. [object_type=%s, object_id=%s]", result_obj.__name__, str(db_object.id))
    return db_object


async def get_item_by_id(id_: str, result_obj: Type[APIDocument], current_user: Optional[User] = None) -> APIDocument:
    if type(id_) == str:
        id_ = ObjectId(id_)
    elif isinstance(id_, ObjectId):
        pass
    elif isinstance(id_, Reference):
        id_ = id_.pk
    else:
        raise Exception(f"unexpected id type: {type(id_)}")
    item = await result_obj.find_one({"_id": id_})
    return item


async def get_items(
    filters: dict,
    result_obj: Type[APIDocument],
    current_user: User,
    size: Optional[int] = None,
    sort_by_field: str = "created_at",
    sort_by_direction: int = -1,
) -> [APIDocument]:
    # TODO: add paging default size to settings

    deleted_filter = {"$or": [{"deleted": {"$exists": False}}, {"deleted": False}]}
    filters.update(deleted_filter)

    items = await result_obj.find(filters).sort(sort_by_field, sort_by_direction).to_list(length=size)
    return items


async def get_item(filters: dict, result_obj: Type[APIDocument], current_user: Optional[User] = None) -> APIDocument:
    deleted_filter = {"$or": [{"deleted": {"$exists": False}}, {"deleted": False}]}
    filters.update(deleted_filter)

    item = await result_obj.find_one(filters)
    return item


async def update_item(item: APIDocument, data: dict, current_user: Optional[User] = None) -> APIDocument:
    item.update(data)
    await item.commit()
    return item


async def delete_item(item: APIDocument) -> APIDocument:
    return await update_item(item, {"deleted": True})
