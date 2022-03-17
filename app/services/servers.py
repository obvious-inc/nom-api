from typing import List, Union

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from app.helpers.guild_xyz import get_user_guild_roles
from app.models.base import APIDocument
from app.models.server import Server, ServerMember
from app.models.user import User
from app.schemas.servers import ServerCreateSchema
from app.services.crud import create_item, get_item, get_item_by_id, get_items


async def create_server(server_model: ServerCreateSchema, current_user: User) -> Union[Server, APIDocument]:
    created_server = await create_item(server_model, result_obj=Server, current_user=current_user, user_field="owner")

    # add owner as server member
    await join_server(server_id=str(created_server.pk), current_user=current_user)

    return created_server


async def join_server(server_id: str, current_user: User) -> ServerMember:
    # 1. check Server's role requirements and integrations (guild.xyz by default)
    server = await get_item_by_id(id_=server_id, result_obj=Server, current_user=current_user)

    # TODO: add proper setup for this
    guild_id = 1985

    # 2. fetch guild.xyz roles for user's wallet
    guild_roles = await get_user_guild_roles(guild_id, user=current_user)

    # 3. associate guild roles with user

    # 4. join server
    # member = ServerMember(server=server, user=current_user)
    # await member.commit()
    # return member

    return None


async def get_user_servers(current_user: User) -> List[Server]:
    server_members = await get_items(
        {"user": current_user.id}, result_obj=ServerMember, current_user=current_user, size=None
    )
    return [await member.server.fetch() for member in server_members]


async def get_server_members(server_id: str, current_user: User):
    user_belongs_to_server = await get_item(
        filters={"server": ObjectId(server_id), "user": current_user.id},
        result_obj=ServerMember,
        current_user=current_user,
    )
    if not user_belongs_to_server:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing permissions")

    server_members = await get_items(
        {"server": ObjectId(server_id)}, result_obj=ServerMember, current_user=current_user, size=None
    )
    return server_members


async def get_servers(current_user: User):
    filters = {
        # filter out private/non-exposed servers
    }
    return await get_items(filters=filters, result_obj=Server, current_user=current_user)
