from typing import List, Union

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from app.helpers.cache_utils import cache
from app.helpers.guild_xyz import is_user_eligible_for_guild
from app.helpers.permissions import DEFAULT_ROLE_PERMISSIONS, user_belongs_to_server
from app.helpers.queue_utils import queue_bg_task
from app.helpers.ws_events import WebSocketServerEvent
from app.models.base import APIDocument
from app.models.channel import Channel
from app.models.server import Server, ServerJoinRule, ServerMember
from app.models.user import Role, User
from app.schemas.channels import ServerChannelCreateSchema
from app.schemas.messages import MessageCreateSchema
from app.schemas.servers import (
    AllowlistJoinRuleCreateSchema,
    GuildXYZJoinRuleCreateSchema,
    ServerCreateSchema,
    ServerUpdateSchema,
)
from app.schemas.users import RoleCreateSchema
from app.services.channels import create_server_channel
from app.services.crud import create_item, get_item, get_item_by_id, get_items, update_item
from app.services.messages import create_message
from app.services.roles import create_role
from app.services.websockets import broadcast_server_event


async def create_server(server_model: ServerCreateSchema, current_user: User) -> Union[Server, APIDocument]:
    created_server = await create_item(server_model, result_obj=Server, current_user=current_user, user_field="owner")

    # add owner as server member
    await join_server(server_id=str(created_server.pk), current_user=current_user, ignore_joining_rules=True)

    default_channel_model = ServerChannelCreateSchema(name="lounge", server=str(created_server.pk))
    default_channel = await create_server_channel(channel_model=default_channel_model, current_user=current_user)
    await update_item(item=created_server, data={"system_channel": default_channel})

    # create default role
    role_schema = RoleCreateSchema(
        name="@everyone", server=str(created_server.pk), permissions=DEFAULT_ROLE_PERMISSIONS
    )
    await create_role(server_id=str(created_server.pk), role_model=role_schema, current_user=current_user)

    await cache.client.hset(f"server:{str(created_server.pk)}", "owner", str(current_user.pk))

    return created_server


async def is_eligible_to_join_server(server_id: str, current_user: User):
    server = await get_item_by_id(id_=server_id, result_obj=Server)
    if not server.join_rules:
        # if no rules, let anyone in
        return True

    user_is_allowed_in = False

    joining_rules = [await role.fetch() for role in server.join_rules]
    for rule in joining_rules:  # type: ServerJoinRule
        if user_is_allowed_in:
            break

        if rule.type == "allowlist":
            user_is_allowed_in = any(
                [current_user.wallet_address.lower() == wl_addr.lower() for wl_addr in rule.allowlist_addresses]
            )
        elif rule.type == "guild_xyz":
            guild_id = rule.guild_xyz_id
            user_is_allowed_in = await is_user_eligible_for_guild(user=current_user, guild_id=guild_id)

    return user_is_allowed_in


async def join_server(server_id: str, current_user: User, ignore_joining_rules: bool = False) -> ServerMember:
    server = await get_item_by_id(id_=server_id, result_obj=Server)
    server_member = await get_item(
        filters={"server": ObjectId(server_id), "user": current_user.id},
        result_obj=ServerMember,
    )
    if server_member:
        return server_member

    if not ignore_joining_rules:
        user_is_allowed_in = await is_eligible_to_join_server(server_id=server_id, current_user=current_user)
        if not user_is_allowed_in:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User cannot join this server")

    default_roles = await get_items(
        filters={"server": server.pk, "name": "@everyone"}, result_obj=Role, sort_by_direction=1, limit=1
    )

    member = ServerMember(server=server, user=current_user, roles=default_roles)
    await member.commit()

    await queue_bg_task(
        broadcast_server_event,
        str(server.id),
        str(current_user.id),
        WebSocketServerEvent.SERVER_USER_JOINED,
        {"user": current_user.dump(), "member": member.dump()},
    )

    if server.owner != current_user:
        message = MessageCreateSchema(server=str(server.id), channel=str(server.system_channel.pk), type=1)
        await create_message(message_model=message, current_user=current_user, ignore_permissions=True)

    return member


async def get_user_servers(current_user: User) -> List[Server]:
    server_members = await get_items(
        {"user": current_user.id}, result_obj=ServerMember, sort_by_field="joined_at", sort_by_direction=1, limit=None
    )
    return [await member.server.fetch() for member in server_members]


async def get_server_members(server_id: str, current_user: User):
    if not await user_belongs_to_server(user=current_user, server_id=server_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing permissions")

    server_members = await get_items({"server": ObjectId(server_id)}, result_obj=ServerMember, limit=None)
    return server_members


async def get_servers(current_user: User):
    # TODO: add flag to filter out private/non-exposed servers
    servers = await get_items(filters={}, result_obj=Server)

    resp_servers = []
    for server in servers:
        server_members = await get_items({"server": server.pk}, result_obj=ServerMember, limit=None)
        resp_servers.append({**server.dump(), "member_count": len(server_members)})

    return resp_servers


async def update_server(server_id: str, update_data: ServerUpdateSchema, current_user: User):
    server = await get_item_by_id(id_=server_id, result_obj=Server)
    if server.owner != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User cannot make changes to this server")

    data = update_data.dict(exclude_unset=True)

    join_rules = data.get("join_rules", [])
    if join_rules:
        db_rules = []
        for rule in data.get("join_rules", []):
            rule_type = rule.get("type")
            if rule_type == "allowlist":
                allowlist_model = AllowlistJoinRuleCreateSchema(**rule)
                db_rule = await create_item(
                    allowlist_model, result_obj=ServerJoinRule, current_user=current_user, user_field=None
                )
            elif rule_type == "guild_xyz":
                guild_model = GuildXYZJoinRuleCreateSchema(**rule)
                db_rule = await create_item(
                    guild_model, result_obj=ServerJoinRule, current_user=current_user, user_field=None
                )
            else:
                raise NotImplementedError(f"unknown rule type: {rule_type}")

            db_rules.append(db_rule)

        data["join_rules"] = db_rules

    system_channel_id = data.get("system_channel")
    if system_channel_id:
        system_channel = await get_item_by_id(id_=system_channel_id, result_obj=Channel)
        if system_channel.kind != "server" or system_channel.server != server:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Cannot use this channel for system messages"
            )

    updated_item = await update_item(item=server, data=data)

    await queue_bg_task(
        broadcast_server_event,
        server_id,
        str(current_user.id),
        WebSocketServerEvent.SERVER_UPDATE,
        {"server": server_id},
    )

    return updated_item
