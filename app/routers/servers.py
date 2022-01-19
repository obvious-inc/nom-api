import http
from typing import List

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_current_user
from app.models.server import Server
from app.models.user import User
from app.schemas.servers import ServerCreateSchema, ServerSchema
from app.services.crud import create_item, get_items

router = APIRouter()


@router.post(
    "", response_description="Create new server", response_model=ServerSchema, status_code=http.HTTPStatus.CREATED
)
async def post_create_server(server: ServerCreateSchema = Body(...), current_user: User = Depends(get_current_user)):
    created_server = await create_item(server, result_obj=Server, current_user=current_user, user_field="owner")
    return created_server


@router.get("", response_description="List all servers", response_model=List[ServerSchema])
async def list_servers(current_user: User = Depends(get_current_user)):
    servers = await get_items(filters={}, result_obj=Server, current_user=current_user)
    return servers
