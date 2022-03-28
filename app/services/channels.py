import http
from datetime import datetime, timezone
from typing import List, Optional, Union

from bson import ObjectId
from fastapi import HTTPException
from starlette import status

from app.helpers.queue_utils import queue_bg_task
from app.helpers.ws_events import WebSocketServerEvent
from app.models.base import APIDocument
from app.models.channel import Channel, ChannelReadState
from app.models.message import Message
from app.models.server import Server, ServerMember
from app.models.user import User
from app.schemas.channels import ChannelReadStateCreateSchema, DMChannelCreateSchema, ServerChannelCreateSchema
from app.services.crud import create_item, delete_item, get_item, get_item_by_id, get_items, update_item
from app.services.websockets import broadcast_channel_event


async def create_dm_channel(channel_model: DMChannelCreateSchema, current_user: User) -> Union[Channel, APIDocument]:
    current_user_id = str(current_user.id)
    if current_user_id not in channel_model.members:
        channel_model.members.insert(0, current_user_id)

    # if same exact dm channel already exists, ignore
    filters = {
        "members": {"$all": [ObjectId(member) for member in channel_model.members]},
    }
    existing_dm_channels = await get_items(filters=filters, result_obj=Channel, current_user=current_user)
    if existing_dm_channels:
        # TODO: return 200 status code
        return existing_dm_channels[0]

    return await create_item(channel_model, result_obj=Channel, current_user=current_user, user_field="owner")


async def create_server_channel(
    channel_model: ServerChannelCreateSchema, current_user: User
) -> Union[Channel, APIDocument]:
    server = await get_item_by_id(id_=str(channel_model.server), result_obj=Server, current_user=current_user)
    if server.owner != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owner can create channels",
        )

    return await create_item(channel_model, result_obj=Channel, current_user=current_user, user_field="owner")


async def create_channel(
    channel_model: Union[DMChannelCreateSchema, ServerChannelCreateSchema], current_user: User
) -> Union[Channel, APIDocument]:
    kind = channel_model.kind
    if isinstance(channel_model, DMChannelCreateSchema):
        return await create_dm_channel(channel_model, current_user)
    elif isinstance(channel_model, ServerChannelCreateSchema):
        return await create_server_channel(channel_model, current_user)
    else:
        raise Exception(f"unexpected channel kind: {kind}")


async def get_server_channels(server_id, current_user: User) -> List[Union[Channel, APIDocument]]:
    return await get_items(filters={"server": ObjectId(server_id)}, result_obj=Channel, current_user=current_user)


async def get_dm_channels(current_user: User, size: Optional[int] = None) -> List[Union[Channel, APIDocument]]:
    return await get_items(
        filters={"members": current_user.pk}, result_obj=Channel, current_user=current_user, size=size
    )


async def delete_channel(channel_id, current_user: User):
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel, current_user=current_user)
    channel_owner = channel.owner
    is_channel_owner = channel_owner == current_user

    if channel.kind == "server":
        server = await channel.server.fetch()
        server_owner = server.owner
        if not is_channel_owner or not current_user == server_owner:
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN)
    elif channel.kind == "dm":
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN)
    else:
        raise Exception(f"unexpected kind of channel: {channel.kind}")

    return await delete_item(item=channel)


async def update_channel_last_message(channel_id, message: Union[Message, APIDocument], current_user: User):
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel, current_user=current_user)
    if not channel.last_message_at or message.created_at > channel.last_message_at:
        await update_item(item=channel, data={"last_message_at": message.created_at}, current_user=current_user)


async def update_channels_read_state(channel_ids: List[str], current_user: User, last_read_at: datetime):
    if not last_read_at:
        last_read_at = datetime.now(timezone.utc)

    for channel_id in channel_ids:
        channel = await get_item_by_id(id_=channel_id, result_obj=Channel)

        read_state = await get_item(filters={"user": current_user.pk, "channel": channel}, result_obj=ChannelReadState)
        if not read_state:
            read_state_model = ChannelReadStateCreateSchema(channel=str(channel.id), last_read_at=last_read_at)
            await create_item(read_state_model, result_obj=ChannelReadState, current_user=current_user)
        else:
            await update_item(item=read_state, data={"last_read_at": last_read_at, "mention_count": 0})


async def create_typing_indicator(channel_id: str, current_user: User) -> None:
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)
    notify = False

    if channel.kind == "server":
        user_member = await get_item(
            filters={"user": current_user, "server": channel.server.pk},
            result_obj=ServerMember,
            current_user=current_user,
        )
        notify = True if user_member else False
    elif channel.kind == "dm":
        notify = str(current_user.id) in channel.members

    if notify:
        await queue_bg_task(
            broadcast_channel_event,
            channel_id,
            str(current_user.id),
            WebSocketServerEvent.USER_TYPING,
            {"user": current_user.dump()},
        )
