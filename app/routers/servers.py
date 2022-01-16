import http
from typing import List

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_current_user
from app.helpers.database import get_db
from app.models.server import Server
from app.models.user import User
from app.schemas.servers import ServerSchema, ServerCreateSchema
from app.services.crud import create_item

router = APIRouter()


@router.post("",
             response_description="Create new server",
             response_model=ServerSchema,
             status_code=http.HTTPStatus.CREATED)
async def create_server(server: ServerCreateSchema = Body(...), db=Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    created_server = await create_item(server, result_obj=Server, current_user=current_user)
    return created_server


@router.get("", response_description="List all servers", response_model=List[ServerSchema])
async def list_servers(db=Depends(get_db), current_user: User = Depends(get_current_user)):
    servers = await db["servers"].find().to_list(50)  # TODO: pagination + set default as setting
    return servers
