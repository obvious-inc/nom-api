import logging
from typing import List, Optional, Sequence, Type, TypeVar

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from pymongo.results import InsertManyResult, UpdateResult
from umongo import Reference

from app.models.base import APIDocument
from app.models.user import User
from app.schemas.base import APIBaseCreateSchema

logger = logging.getLogger(__name__)

APIDocumentType = TypeVar("APIDocumentType", bound=APIDocument)


async def create_item(
    item: APIBaseCreateSchema,
    result_obj: Type[APIDocumentType],
    current_user: Optional[User] = None,
    user_field: Optional[str] = "user",
) -> APIDocumentType:
    db_object = result_obj(**item.dict())
    if user_field:
        db_object[user_field] = current_user
    await db_object.commit()
    logger.info("Object created. [object_type=%s, object_id=%s]", result_obj.__name__, str(db_object.id))
    return db_object


async def create_items(
    items: Sequence[APIBaseCreateSchema],
    result_obj: Type[APIDocumentType],
    current_user: Optional[User] = None,
    user_field: Optional[str] = "user",
) -> List[ObjectId]:
    db_objects = []
    for item in items:
        db_object = result_obj(**item.dict())
        if user_field:
            db_object[user_field] = current_user
        await db_object.io_validate()
        db_objects.append(db_object)

    mongo_objects = [obj.to_mongo() for obj in db_objects]
    created_result = await result_obj.collection.insert_many(mongo_objects)  # type: InsertManyResult
    created_object_ids = created_result.inserted_ids

    logger.info("%d objects created. [object_type=%s", len(created_object_ids), result_obj.__name__)

    return created_object_ids


async def get_item_by_id(
    id_: str, result_obj: Type[APIDocumentType], current_user: Optional[User] = None
) -> APIDocumentType:
    if type(id_) == str:
        try:
            id_ = ObjectId(id_)
        except InvalidId:
            raise TypeError("id_ must be ObjectId")
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
    result_obj: Type[APIDocumentType],
    current_user: Optional[User],
    size: Optional[int] = None,
    sort_by_field: str = "created_at",
    sort_by_direction: int = -1,
) -> List[APIDocumentType]:
    # TODO: add paging default size to settings

    deleted_filter = {"$or": [{"deleted": {"$exists": False}}, {"deleted": False}]}
    filters.update(deleted_filter)

    item_query = result_obj.find(filters).sort(sort_by_field, sort_by_direction)

    if size:
        item_query.limit(size)

    items = await item_query.to_list(length=size)

    return items


async def get_item(
    filters: dict, result_obj: Type[APIDocumentType], current_user: Optional[User] = None
) -> APIDocumentType:
    deleted_filter = {"$or": [{"deleted": {"$exists": False}}, {"deleted": False}]}
    filters.update(deleted_filter)

    item = await result_obj.find_one(filters)
    return item


async def update_item(item: APIDocumentType, data: dict, current_user: Optional[User] = None) -> APIDocumentType:
    local_data = dict(data)
    none_fields = [field for field, value in local_data.items() if value is None]
    for field in none_fields:
        del item[field]
        local_data.pop(field)

    item.update(local_data)
    await item.commit()
    return item


async def find_and_update_item(filters: dict, data: dict, result_obj: Type[APIDocumentType]) -> APIDocumentType:
    updated_item = await result_obj.collection.find_one_and_update(
        filter=filters, update=data, return_document=ReturnDocument.AFTER
    )
    return updated_item


async def delete_item(item: APIDocumentType) -> APIDocumentType:
    return await update_item(item, {"deleted": True})


async def delete_items(filters: dict, result_obj: Type[APIDocumentType], current_user: Optional[User] = None):
    updated_result = await result_obj.collection.update_many(
        filter=filters, update={"$set": {"deleted": True}}
    )  # type: UpdateResult

    logger.info("%d objects deleted. [object_type=%s", updated_result.modified_count, result_obj.__name__)
