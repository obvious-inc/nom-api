from app.helpers.websockets import pusher_client
from app.models.message import Message
from app.models.server import Server, ServerMember
from app.models.user import User
from app.services.channels import get_server_channels
from app.services.crud import get_item, get_items
from app.services.servers import get_server_members, get_user_servers


async def get_online_channels(message: Message, current_user: User) -> [str]:
    server = message.server  # type: Server
    server_members = await get_items(filters={"server": server.pk}, result_obj=ServerMember, current_user=current_user)
    server_users = [await member.user.fetch() for member in server_members]
    channels = []
    for user in server_users:  # type: User
        channels.extend(user.online_channels)
    return channels


async def pusher_broadcast_messages(channels: [str], event_name: str, data: dict):
    while len(channels) > 0:
        push_channels = channels[:90]
        try:
            await pusher_client.trigger(push_channels, event_name, data)
        except Exception as e:
            print(f"problems triggering Pusher events: {e}")
        channels = channels[90:]


async def broadcast_new_message(
    message: Message,
    current_user: User,
):
    event_name = "MESSAGE_CREATE"
    ws_data = message.dump()
    channels = await get_online_channels(message, current_user)

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

    push_channels = [channel]
    await pusher_broadcast_messages(push_channels, event_name, data)
