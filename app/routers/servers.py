import http
from typing import List

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.servers import ServerCreateSchema, ServerMemberSchema, ServerSchema
from app.services.servers import create_server, get_server_members

router = APIRouter()


@router.post(
    "", response_description="Create new server", response_model=ServerSchema, status_code=http.HTTPStatus.CREATED
)
async def post_create_server(server: ServerCreateSchema = Body(...), current_user: User = Depends(get_current_user)):
    return await create_server(server, current_user=current_user)


@router.get(
    "/{server_id}/members",
    response_description="List server members",
    response_model=List[ServerMemberSchema],
)
async def get_list_server_members(server_id, current_user: User = Depends(get_current_user)):
    return await get_server_members(server_id, current_user=current_user)
