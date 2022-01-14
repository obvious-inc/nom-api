import http
from typing import List

from fastapi import APIRouter, Body, Depends
from fastapi.encoders import jsonable_encoder

from app.dependencies import get_current_user
from app.helpers.database import get_db
from app.models.server import ServerModel

router = APIRouter()


@router.post("",
             response_description="Create new server",
             response_model=ServerModel,
             status_code=http.HTTPStatus.CREATED)
async def create_server(server: ServerModel = Body(...), db=Depends(get_db),
                        current_user: str = Depends(get_current_user)):
    server = jsonable_encoder(server)
    new_server = await db["servers"].insert_one(server)
    created_server = await db["servers"].find_one({"_id": new_server.inserted_id})
    return created_server


@router.get("", response_description="List all servers", response_model=List[ServerModel])
async def list_servers(db=Depends(get_db), current_user: str = Depends(get_current_user)):
    servers = await db["servers"].find().to_list(50)  # TODO: pagination + set default as setting
    return servers
