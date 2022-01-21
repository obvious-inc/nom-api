from typing import Union

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from app.models.base import APIDocument
from app.models.server import Server, ServerMember
from app.models.user import User
from app.schemas.servers import ServerCreateSchema
from app.services.crud import create_item


async def create_server(server_model: ServerCreateSchema, current_user: User) -> Union[Server, APIDocument]:
    created_server = await create_item(server_model, result_obj=Server, current_user=current_user, user_field="owner")

    # add owner as server member
    await join_server(created_server, current_user)

    return created_server


async def join_server(server: Union[Server, APIDocument], current_user: User, display_name: str = None) -> ServerMember:
    member = ServerMember(server=server, user=current_user, display_name=display_name or current_user.display_name)
    await member.commit()
    return member


async def get_user_servers(current_user: User) -> [Server]:
    server_members = await ServerMember.find({"user": current_user.id}).to_list(length=None)
    return [await member.server.fetch() for member in server_members]


async def get_server_members(server_id: str, current_user: User):
    user_belongs_to_server = await ServerMember.find_one({"server": ObjectId(server_id), "user": current_user.id})
    if not user_belongs_to_server:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing permissions")

    server_members = await ServerMember.find({"server": ObjectId(server_id)}).to_list(length=None)
    return server_members
