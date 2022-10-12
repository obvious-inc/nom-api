import http
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional, Union, cast

from bson import ObjectId
from fastapi import HTTPException
from sentry_sdk import capture_exception
from starlette import status

from app.helpers import cloudflare
from app.helpers.cache_utils import cache
from app.helpers.channels import convert_permission_object_to_cached
from app.helpers.permissions import fetch_user_permissions, user_belongs_to_server
from app.helpers.queue_utils import queue_bg_task
from app.helpers.w3 import checksum_address
from app.helpers.ws_events import WebSocketServerEvent
from app.models.base import APIDocument
from app.models.channel import Channel, ChannelReadState
from app.models.common import PermissionOverwrite
from app.models.section import Section
from app.models.server import ServerMember
from app.models.user import User
from app.schemas.channels import (
    ChannelBulkReadStateCreateSchema,
    ChannelReadStateCreateSchema,
    ChannelUpdateSchema,
    DMChannelCreateSchema,
    ServerChannelCreateSchema,
    TopicChannelCreateSchema,
)
from app.schemas.messages import SystemMessageCreateSchema
from app.schemas.permissions import PermissionUpdateSchema
from app.schemas.users import UserCreateSchema
from app.services.crud import (
    create_item,
    delete_item,
    find_and_update_item,
    get_item,
    get_item_by_id,
    get_items,
    update_item,
)
from app.services.messages import create_message
from app.services.users import create_user, get_user_by_wallet_address
from app.services.websockets import broadcast_channel_event

logger = logging.getLogger(__name__)


async def parse_member_list(members: List[str], create_if_not_user: bool = True):
    final_member_list = []
    for member in members:
        if re.match(r"^0x[a-fA-F\d]{40}$", member):
            wallet_addr = checksum_address(member)
            user = await get_user_by_wallet_address(wallet_address=wallet_addr)
            if not user and create_if_not_user:
                user = await create_user(user_model=UserCreateSchema(wallet_address=wallet_addr), fetch_ens=True)
        else:
            user = await get_item_by_id(id_=member, result_obj=User)

        if user not in final_member_list:
            final_member_list.append(user)

    return final_member_list


async def create_dm_channel(channel_model: DMChannelCreateSchema, current_user: User) -> Union[Channel, APIDocument]:
    channel_model.members = await parse_member_list(members=channel_model.members or [])
    if current_user not in channel_model.members:
        channel_model.members.insert(0, current_user)

    # if same exact dm channel already exists, ignore
    filters = {
        "kind": "dm",
        "members": {
            "$size": len(channel_model.members),
            "$all": channel_model.members,
        },
    }
    existing_dm_channels = await get_items(filters=filters, result_obj=Channel)
    if existing_dm_channels:
        # TODO: return 200 status code
        return existing_dm_channels[0]

    return await create_item(channel_model, result_obj=Channel, current_user=current_user, user_field="owner")


async def create_server_channel(
    channel_model: ServerChannelCreateSchema, current_user: User
) -> Union[Channel, APIDocument]:
    return await create_item(channel_model, result_obj=Channel, current_user=current_user, user_field="owner")


async def create_topic_channel(
    channel_model: TopicChannelCreateSchema, current_user: User
) -> Union[Channel, APIDocument]:
    channel_model.members = await parse_member_list(members=channel_model.members or [])
    if not channel_model.members:
        channel_model.members = [current_user.pk]
    else:
        if current_user.pk not in channel_model.members:
            channel_model.members.insert(0, current_user.pk)
    return await create_item(channel_model, result_obj=Channel, current_user=current_user, user_field="owner")


async def create_channel(
    channel_model: Union[ServerChannelCreateSchema, TopicChannelCreateSchema, DMChannelCreateSchema],
    current_user: User,
) -> Union[Channel, APIDocument]:
    if channel_model.kind == "dm":
        channel_model = cast(DMChannelCreateSchema, channel_model)
        return await create_dm_channel(channel_model, current_user)
    elif channel_model.kind == "server":
        channel_model = cast(ServerChannelCreateSchema, channel_model)
        return await create_server_channel(channel_model=channel_model, current_user=current_user)
    elif channel_model.kind == "topic":
        channel_model = cast(TopicChannelCreateSchema, channel_model)
        return await create_topic_channel(channel_model=channel_model, current_user=current_user)
    else:
        raise Exception(f"unexpected channel kind: {channel_model.kind}")


async def get_server_channels(server_id, current_user: User) -> List[Union[Channel, APIDocument]]:
    if not await user_belongs_to_server(user=current_user, server_id=server_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing permissions")

    return await get_items(filters={"server": ObjectId(server_id)}, result_obj=Channel, limit=None)


async def get_dm_channels(current_user: User, limit: Optional[int] = None) -> List[Union[Channel, APIDocument]]:
    return await get_items(filters={"members": current_user.pk, "kind": "dm"}, result_obj=Channel, limit=limit)


async def get_all_member_channels(current_user: User, limit: Optional[int] = None) -> List[Union[Channel, APIDocument]]:
    return await get_items(filters={"members": current_user.pk}, result_obj=Channel, limit=limit)


async def delete_channel(channel_id, current_user: User):
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)
    channel_owner = channel.owner
    is_channel_owner = channel_owner == current_user

    if channel.kind == "server":
        server = await channel.server.fetch()
        server_owner = server.owner
        if not is_channel_owner and not current_user == server_owner:
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN)
    elif channel.kind == "dm":
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN)
    elif channel.kind == "topic":
        if not is_channel_owner:
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN)
    else:
        raise Exception(f"unexpected kind of channel: {channel.kind}")

    deleted_channel = await delete_item(item=channel)

    try:
        section = await get_item(filters={"channels": ObjectId(channel_id)}, result_obj=Section)
        if section:
            section.channels.remove(channel)
            await section.commit()
    except Exception as e:
        logger.warning("trying to delete channel from section failed: %s", e)
        capture_exception(e)

    await queue_bg_task(
        broadcast_channel_event,
        channel_id,
        str(current_user.id),
        WebSocketServerEvent.CHANNEL_DELETED,
        {"channel": channel_id},
    )

    return deleted_channel


async def bulk_mark_channels_as_read(ack_data: ChannelBulkReadStateCreateSchema, current_user: User):
    await update_channels_read_state(
        channel_ids=ack_data.channels, current_user=current_user, last_read_at=ack_data.last_read_at
    )


async def mark_channel_as_read(channel_id: str, last_read_at: Optional[datetime], current_user: User):
    await update_channels_read_state(channel_ids=[channel_id], current_user=current_user, last_read_at=last_read_at)


async def update_channels_read_state(channel_ids: List[str], current_user: User, last_read_at: Optional[datetime]):
    if not last_read_at:
        last_read_at = datetime.now(timezone.utc)

    for channel_id in channel_ids:
        # TODO: check if any mentions present after last_read_at. if so, change mention_count below
        update_data = {"$set": {"last_read_at": last_read_at, "mention_count": 0}}
        updated_item = await find_and_update_item(
            filters={"user": current_user.pk, "channel": ObjectId(channel_id)},
            data=update_data,
            result_obj=ChannelReadState,
        )

        if not updated_item:
            read_state_model = ChannelReadStateCreateSchema(channel=channel_id, last_read_at=last_read_at)
            await create_item(read_state_model, result_obj=ChannelReadState, current_user=current_user)


async def create_typing_indicator(channel_id: str, current_user: User) -> None:
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)
    notify = False

    if channel.kind == "server":
        user_member = await get_item(
            filters={"user": current_user, "server": channel.server.pk},
            result_obj=ServerMember,
        )
        notify = True if user_member else False
    elif channel.kind == "dm" or channel.kind == "topic":
        notify = current_user in channel.members

    if notify:
        await queue_bg_task(
            broadcast_channel_event,
            channel_id,
            str(current_user.id),
            WebSocketServerEvent.USER_TYPING,
            {"user": await current_user.to_dict(exclude_fields=["pfp"])},
        )


async def update_channel(channel_id: str, update_data: ChannelUpdateSchema, current_user: User):
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)

    data = update_data.dict(exclude_unset=True)

    if channel.kind == "server":
        server = await channel.server.fetch()
        if channel.owner != current_user and server.owner != current_user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User cannot change this channel")
    elif channel.kind == "dm" or channel.kind == "topic":
        if current_user not in channel.members or channel.owner != current_user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User cannot change this channel")
    else:
        raise Exception(f"unknown channel kind: {channel.kind}")

    avatar = data.get("avatar", None)
    if avatar is not None and avatar != "":
        if avatar.startswith("http"):
            cf_response = await cloudflare.upload_image_url(avatar)
            logger.info(f"uploaded avatar image {avatar} to cloudflare: {cf_response}")
            data["avatar"] = cf_response.get("id")

    updated_item = await update_item(item=channel, data=data)

    await queue_bg_task(
        broadcast_channel_event,
        channel_id,
        str(current_user.id),
        WebSocketServerEvent.CHANNEL_UPDATE,
        {"channel": updated_item.dump()},
    )

    updated_fields = list(data.keys())
    if len(updated_fields) == 1:
        message = SystemMessageCreateSchema(channel=channel_id, type=5, updates=data)
        await create_message(message_model=message, current_user=current_user)

    return updated_item


async def get_channel(channel_id: str):
    return await get_item_by_id(id_=channel_id, result_obj=Channel)


async def invite_members_to_channel(channel_id: str, members: List[str], current_user: User):
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)
    if channel.kind != "topic":
        raise Exception(f"cannot change members of channel type: {channel.kind}")

    parsed_member_list = await parse_member_list(members=members)

    new_users = []
    final_channel_members = [m.pk for m in channel.members]
    for member in parsed_member_list:
        if member not in channel.members:
            final_channel_members.append(member.pk)
            new_users.append(member)

    await update_item(item=channel, data={"members": final_channel_members})
    await cache.client.hset(f"channel:{channel_id}", "members", ",".join([str(m) for m in final_channel_members]))

    for new_user in new_users:
        await queue_bg_task(
            broadcast_channel_event,
            channel_id,
            str(new_user.pk),
            WebSocketServerEvent.CHANNEL_USER_INVITED,
            {"channel": channel_id, "user": await new_user.to_dict(exclude_fields=["pfp"])},
        )

        message = SystemMessageCreateSchema(channel=channel_id, type=1, inviter=str(current_user.pk))
        await create_message(message_model=message, current_user=new_user)


async def kick_member_from_channel(channel_id: str, member_id: str):
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)
    if channel.kind != "topic":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"cannot kick members from channel type: {channel.kind}"
        )

    if str(channel.owner.pk) == member_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot kick owner from channel")

    current_channel_members = [str(m.pk) for m in channel.members]

    if member_id not in current_channel_members:
        raise Exception(f"member {member_id} is not in channel {channel_id}")

    final_channel_members = [m for m in current_channel_members if m != member_id]
    await update_item(item=channel, data={"members": final_channel_members})
    await cache.client.hset(f"channel:{channel_id}", "members", ",".join([str(m) for m in final_channel_members]))


async def update_channel_permissions(channel_id: str, update_data: List[PermissionUpdateSchema]):
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)

    ows = []
    for permission in update_data:
        ow = PermissionOverwrite(**permission.dict(exclude_none=True))
        ows.append(ow)

    updated = await update_item(item=channel, data={"permission_overwrites": ows})

    cache_ps = await convert_permission_object_to_cached(updated)
    await cache.client.hset(f"channel:{channel_id}", "permissions", cache_ps)


async def join_channel(channel_id: str, current_user: User):
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)
    if channel.kind != "topic":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"cannot join channel of type: {channel.kind}"
        )

    if current_user in channel.members:
        return

    current_channel_members = [m.pk for m in channel.members]
    current_channel_members.append(current_user.pk)

    await update_item(item=channel, data={"members": current_channel_members})
    await cache.client.hset(f"channel:{channel_id}", "members", ",".join([str(m) for m in current_channel_members]))

    await queue_bg_task(
        broadcast_channel_event,
        channel_id,
        str(current_user.pk),
        WebSocketServerEvent.CHANNEL_USER_JOINED,
        {"channel": channel_id, "user": await current_user.to_dict(exclude_fields=["pfp"])},
    )

    message = SystemMessageCreateSchema(channel=channel_id, type=1)
    await create_message(message_model=message, current_user=current_user)


async def get_channel_permissions(channel_id: str, current_user_or_exception: Union[User, Exception, None]):
    if isinstance(current_user_or_exception, Exception):
        raise current_user_or_exception

    user_id = str(current_user_or_exception.pk) if current_user_or_exception else None
    return await fetch_user_permissions(channel_id=channel_id, server_id=None, user_id=user_id)


async def get_channel_members(channel_id: str):
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)
    if channel.kind not in ["topic", "dm"]:
        raise Exception(f"cannot get members of channel type: {channel.kind}")

    return await get_items(filters={"_id": {"$in": [user.pk for user in channel.members]}}, result_obj=User, limit=None)


async def get_user_channels(current_user: User):
    return await get_items(filters={"members": current_user.pk}, result_obj=Channel, limit=None)
