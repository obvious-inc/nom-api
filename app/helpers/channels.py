from typing import List

from app.models.channel import Channel
from app.models.server import ServerMember
from app.models.user import User
from app.services.crud import get_item, get_items


async def is_user_in_channel(user: User, channel: Channel) -> bool:
    if channel.kind == "server":
        # TODO: need fine grain permissions per channel, rather than per server
        user_in_server = await get_item(
            filters={"server": channel.server.pk, "user": user.id},
            result_obj=ServerMember,
        )

        if not user_in_server:
            return False
        else:
            return True
    elif channel.kind == "dm":
        return str(user.id) in channel.members

    return False


async def get_channel_online_users(channel: Channel) -> List[User]:
    users = await get_channel_users(channel)
    return [user for user in users if user.status == "online"]


async def get_channel_users(channel: Channel) -> List[User]:
    members = []
    if channel.kind == "dm":
        members = channel.members
    elif channel.kind == "server":
        members = await get_items(filters={"server": channel.server.pk}, result_obj=ServerMember, current_user=None)

    users = [await member.user.fetch() for member in members]
    return users
