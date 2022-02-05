import logging
from typing import List, Optional, Union

from app.helpers.websockets import pusher_client
from app.helpers.ws_events import WebSocketServerEvent
from app.models.base import APIDocument
from app.models.channel import Channel, ChannelReadState
from app.models.message import Message
from app.models.server import Server, ServerMember
from app.models.user import User
from app.services.channels import get_server_channels
from app.services.crud import get_item_by_id, get_items
from app.services.servers import get_server_members, get_user_servers
from app.services.users import get_user_by_id

logger = logging.getLogger(__name__)


async def get_online_channels(message: Union[Message, APIDocument], current_user: User) -> List[str]:
    server = message.server  # type: Server
    if server:
        members = await get_items(filters={"server": server.pk}, result_obj=ServerMember, current_user=current_user)
        users = [await member.user.fetch() for member in members]
    else:
        channel = await message.channel.fetch()
        users = [await member.fetch() for member in channel.members]

    channels = []
    for user in users:  # type: User
        channels.extend(user.online_channels)
    return channels


async def pusher_broadcast_messages(
    event: WebSocketServerEvent,
    current_user: User,
    data: dict,
    message: Optional[Message] = None,
    pusher_channel: Optional[str] = None,
):
    pusher_channels = current_user.online_channels
    if message:
        pusher_channels = await get_online_channels(message=message, current_user=current_user)

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
    data = {"user": current_user.dump(), "servers": []}

    servers = await get_user_servers(current_user=current_user)
    for server in servers:
        server_data = {"id": str(server.id), "name": server.name, "owner": str(server.owner.pk)}
        channels = await get_server_channels(server_id=str(server.id), current_user=current_user)
        members = await get_server_members(server_id=str(server.id), current_user=current_user)

        server_data.update(
            {
                "channels": [
                    {
                        "id": str(channel.id),
                        "last_message_at": channel.last_message_at.isoformat() if channel.last_message_at else None,
                        "name": channel.name,
                    }
                    for channel in channels
                ],
                "members": [
                    {
                        "id": str(member.id),
                        "user": str(member.user.pk),
                        "server": str(member.server.pk),
                        "display_name": member.display_name,
                    }
                    for member in members
                ],
            }
        )

        data["servers"].append(server_data)

    read_states = await get_items(
        filters={"user": current_user}, result_obj=ChannelReadState, current_user=current_user, size=None
    )
    data["read_states"] = [
        {"channel": str(read_state.channel.pk), "last_read_at": read_state.last_read_at.isoformat()}
        for read_state in read_states
    ]

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
