import http
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.stars import StarCreateSchema, StarSchema
from app.services.stars import create_star, delete_star, get_stars

router = APIRouter()


@router.post(
    "",
    response_description="Star message, channel or server",
    response_model=StarSchema,
    status_code=http.HTTPStatus.CREATED,
)
async def post_create_star(star: StarCreateSchema, current_user: User = Depends(get_current_user)):
    return await create_star(star, current_user=current_user)


@router.get("", summary="List all user's stars", response_model=List[StarSchema], status_code=http.HTTPStatus.OK)
async def get_fetch_stars(
    star_type: Optional[str] = Query(None, alias="type"), current_user: User = Depends(get_current_user)
):
    return await get_stars(current_user=current_user, stars_type=star_type)


@router.delete("/{star_id}", summary="Remove star", status_code=http.HTTPStatus.NO_CONTENT)
async def delete_remove_star(star_id: str, current_user: User = Depends(get_current_user)):
    await delete_star(star_id, current_user=current_user)
