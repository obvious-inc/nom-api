import logging
from typing import Union

from starlette.datastructures import FormData

from app.helpers.websockets import pusher_client
from app.models.base import APIDocument
from app.models.message import Message
from app.models.server import Server, ServerMember
from app.models.user import OnlineChannel, User
from app.services.channels import get_dm_channels, get_server_channels
from app.services.crud import get_item, get_item_by_id, get_items
from app.services.servers import get_server_members, get_user_servers
from app.services.users import get_user_by_id

logger = logging.getLogger(__name__)


async def create_online_channel(form_data: FormData, current_user: User):
    mutable_form_data = dict(form_data)
    channel_name = mutable_form_data.pop("channel_name")
    socket_id = mutable_form_data.pop("socket_id")
    provider = mutable_form_data.pop("provider")

    online_channel = OnlineChannel(
        channel_name=channel_name, socket_id=socket_id, provider=provider, ready=False, props=mutable_form_data
    )

    current_user.online_channels.append(online_channel)
    await current_user.commit()


async def get_online_channels(message: Union[Message, APIDocument], current_user: User) -> [str]:
    server = message.server  # type: Server
    if server:
        members = await get_items(filters={"server": server.pk}, result_obj=ServerMember, current_user=current_user)
        users = [await member.user.fetch() for member in members]
    else:
        channel = await message.channel.fetch()
        users = [await member.fetch() for member in channel.members]

    channels = []
    for user in users:  # type: User
        ready_channels = [channel.channel_name for channel in user.online_channels if channel.ready]
        channels.extend(ready_channels)
    return channels


async def pusher_broadcast_messages(channels: [str], event_name: str, data: dict):
    while len(channels) > 0:
        push_channels = channels[:90]
        try:
            await pusher_client.trigger(push_channels, event_name, data)
        except Exception:
            logger.exception("Problem broadcasting event to Pusher channel. [event_name=%s]", event_name)
        channels = channels[90:]
    logger.debug("Event broadcast successful. [event_name=%s]", event_name)


async def broadcast_new_message(
    message_id: str,
    author_id: str,
):
    user = await get_user_by_id(user_id=author_id)
    message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=user)
    event_name = "MESSAGE_CREATE"
    ws_data = message.dump()
    channels = await get_online_channels(message=message, current_user=user)
    await pusher_broadcast_messages(channels, event_name=event_name, data=ws_data)


async def broadcast_connection_ready(current_user: User, channel: str):
    event_name = "CONNECTION_READY"
    data = {"user": current_user.dump(), "servers": []}

    servers = await get_user_servers(current_user=current_user)
    for server in servers:
        server_data = server.dump()
        channels = await get_server_channels(server_id=str(server.id), current_user=current_user)
        members = await get_server_members(server_id=str(server.id), current_user=current_user)
        user_member = await get_item(
            filters={"server": server.id, "user": current_user.id},
            result_obj=ServerMember,
            current_user=current_user,
        )

        server_data.update(
            {
                "channels": [channel.dump() for channel in channels],
                "members": [member.dump() for member in members],
                "member": user_member.dump() if user_member else {},
            }
        )

        data["servers"].append(server_data)

    dm_channels = await get_dm_channels(current_user=current_user)
    data["dms"] = [dm_channel.dump() for dm_channel in dm_channels]
    push_channels = [channel]
    await pusher_broadcast_messages(push_channels, event_name, data)


async def broadcast_new_reaction(message_id, reaction, author_id):
    user = await get_user_by_id(user_id=author_id)
    message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=user)
    event_name = "MESSAGE_REACTION_ADD"
    ws_data = {"message": message_id, "user": user.dump(), "reaction": reaction.dump()}
    channels = await get_online_channels(message=message, current_user=user)
    await pusher_broadcast_messages(channels, event_name=event_name, data=ws_data)


async def broadcast_remove_reaction(message_id, reaction, author_id):
    user = await get_user_by_id(user_id=author_id)
    message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=user)
    event_name = "MESSAGE_REACTION_REMOVE"
    ws_data = {"message": message_id, "user": user.dump(), "reaction": reaction.dump()}
    channels = await get_online_channels(message=message, current_user=user)
    await pusher_broadcast_messages(channels, event_name=event_name, data=ws_data)
