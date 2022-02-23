import logging
from typing import List, Optional, Union

from app.helpers.websockets import pusher_client
from app.helpers.ws_events import WebSocketServerEvent
from app.models.base import APIDocument
from app.models.channel import Channel
from app.models.message import Message
from app.models.server import Server, ServerMember
from app.models.user import User
from app.services.base import get_connection_ready_data
from app.services.crud import get_item_by_id, get_items
from app.services.users import get_user_by_id

logger = logging.getLogger(__name__)


async def get_online_channels(
    message: Optional[Union[Message, APIDocument]],
    current_user: User,
    servers: Optional[List[Server]] = None,
) -> List[str]:

    if message:
        server = message.server  # type: Server
        if server:
            members = await get_items(filters={"server": server.pk}, result_obj=ServerMember, current_user=current_user)
            users = [await member.user.fetch() for member in members]
        else:
            channel = await message.channel.fetch()
            users = [await member.fetch() for member in channel.members]
    elif servers:
        members = []
        [
            members.extend(
                await get_items(filters={"server": server.pk}, result_obj=ServerMember, current_user=current_user)
            )
            for server in servers
        ]

        users = [await member.user.fetch() for member in members]
    else:
        raise ValueError("expected one of 'message' or 'servers'")

    channels = []
    for user in users:  # type: User
        channels.extend(user.online_channels)
    return channels


async def pusher_broadcast_messages(
    event: WebSocketServerEvent,
    current_user: User,
    data: dict,
    message: Optional[Message] = None,
    servers: Optional[List[Server]] = None,
    pusher_channel: Optional[str] = None,
):
    pusher_channels = current_user.online_channels
    if message or servers:
        pusher_channels = await get_online_channels(message=message, servers=servers, current_user=current_user)

    if pusher_channel:
        pusher_channels = [pusher_channel]

    event_name: str = event.value
    has_errors = False

    while len(pusher_channels) > 0:
        push_channels = pusher_channels[:90]
        try:
            await pusher_client.trigger(push_channels, event_name, data)
        except Exception:
            logger.exception("Problem broadcasting event to Pusher channel. [event_name=%s]", event_name)
            has_errors = True
        pusher_channels = pusher_channels[90:]

    if not has_errors:
        logger.debug("Event broadcast successful. [event_name=%s]", event_name)


async def broadcast_message_event(
    message_id: str, user_id: str, event: WebSocketServerEvent, custom_data: Optional[dict] = None
):
    user = await get_user_by_id(user_id=user_id)
    message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=user)

    event_data = {"message": message.dump()}
    if custom_data:
        event_data.update(custom_data)

    await pusher_broadcast_messages(event=event, data=event_data, current_user=user, message=message)


async def broadcast_connection_ready(current_user: User, channel: str):
    data = await get_connection_ready_data(current_user=current_user)
    await pusher_broadcast_messages(
        event=WebSocketServerEvent.CONNECTION_READY, data=data, current_user=current_user, pusher_channel=channel
    )


async def broadcast_channel_event(channel_id: str, user_id: str, event: WebSocketServerEvent, custom_data: dict):
    user = await get_user_by_id(user_id=user_id)
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel, current_user=user)

    event_data = {"channel": channel.dump()}
    if custom_data:
        event_data.update(custom_data)

    await pusher_broadcast_messages(event=event, data=event_data, current_user=user)


async def broadcast_user_event(user_id: str, event: WebSocketServerEvent, custom_data: dict) -> None:
    user = await get_user_by_id(user_id=user_id)
    event_data = {"user": user.dump()}
    if custom_data:
        event_data.update(custom_data)

    server_members = await get_items({"user": user.id}, result_obj=ServerMember, current_user=user, size=None)
    servers = [member.server for member in server_members]

    await pusher_broadcast_messages(event=event, data=event_data, current_user=user, servers=servers)
