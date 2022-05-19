import http
from typing import List, Optional, Union

from bson import ObjectId
from fastapi import HTTPException

from app.models.base import APIDocument
from app.models.star import Star
from app.models.user import User
from app.schemas.stars import StarCreateSchema
from app.services.crud import create_item, delete_item, get_item_by_id, get_items


async def create_star(star_model: StarCreateSchema, current_user: User) -> Union[Star, APIDocument]:
    star_type = ""
    filters = {}
    if getattr(star_model, "message"):
        star_type = "message"
        filters["message"] = ObjectId(star_model.message)
    elif getattr(star_model, "channel"):
        star_type = "channel"
        filters["channel"] = ObjectId(star_model.channel)
    elif getattr(star_model, "server"):
        star_type = "server"
        filters["server"] = ObjectId(star_model.server)
    else:
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail=f"unexpected star type: {star_type}")

    star_model.type = star_type
    filters["type"] = star_type
    filters["user"] = current_user.pk

    existing_star = await get_items(filters=filters, result_obj=Star)
    if existing_star:
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="Star already exists")

    return await create_item(item=star_model, result_obj=Star, current_user=current_user)


async def get_stars(current_user: User, stars_type: Optional[str] = None) -> List[Star]:
    filters = {"user": current_user.pk}
    if stars_type:
        filters["type"] = stars_type
    return await get_items(filters=filters, result_obj=Star)


async def delete_star(star_id: str, current_user: User):
    star = await get_item_by_id(id_=star_id, result_obj=Star)
    if not star:
        return
    can_delete = star.user == current_user
    if not can_delete:
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN)

    await delete_item(item=star)
