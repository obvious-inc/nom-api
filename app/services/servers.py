from typing import List, Union

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from app.helpers.guild_xyz import is_user_eligble_for_guild
from app.helpers.queue_utils import queue_bg_task
from app.helpers.ws_events import WebSocketServerEvent
from app.models.base import APIDocument
from app.models.server import Server, ServerJoinRule, ServerMember
from app.models.user import User
from app.schemas.servers import ServerCreateSchema
from app.services.crud import create_item, get_item, get_item_by_id, get_items
from app.services.websockets import broadcast_server_event


async def create_server(server_model: ServerCreateSchema, current_user: User) -> Union[Server, APIDocument]:
    created_server = await create_item(server_model, result_obj=Server, current_user=current_user, user_field="owner")

    # add owner as server member
    await join_server(server_id=str(created_server.pk), current_user=current_user)

    return created_server


async def join_server(server_id: str, current_user: User) -> ServerMember:
    server = await get_item_by_id(id_=server_id, result_obj=Server, current_user=current_user)
    server_member = await get_item(
        filters={"server": ObjectId(server_id), "user": current_user.id},
        result_obj=ServerMember,
        current_user=current_user,
    )
    if server_member:
        return server_member

    user_is_allowed_in = False

    joining_rules = server.join_rules
    if not joining_rules:
        # if no rules, let anyone in
        user_is_allowed_in = True

    for rule in joining_rules:  # type: ServerJoinRule
        if rule.type == "whitelist":
            user_is_allowed_in = any(
                [current_user.wallet_address.lower() == wl_addr.lower() for wl_addr in rule.whitelist_addresses]
            )
        elif rule.type == "guild_xyz":
            guild_id = rule.guild_xyz_id
            user_is_allowed_in = await is_user_eligble_for_guild(user=current_user, guild_id=guild_id)

    if not user_is_allowed_in:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User cannot join this server")

    member = ServerMember(server=server, user=current_user)
    await member.commit()

    await queue_bg_task(
        broadcast_server_event,
        str(server.id),
        str(current_user.id),
        WebSocketServerEvent.SERVER_USER_JOINED,
        {"user": current_user.dump(), "member": member.dump()},
    )

    return member


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
