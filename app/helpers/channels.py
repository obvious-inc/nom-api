import json
from typing import Any, Dict, List, Optional

from app.helpers.cache_utils import cache
from app.models.channel import Channel
from app.models.server import ServerMember
from app.models.user import User
from app.services.crud import get_item, get_item_by_id, get_items


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
        return user in channel.members
    elif channel.kind == "url":
        # TODO: temporary
        return user == channel.owner

    return False


async def get_channel_online_users(channel: Channel) -> List[User]:
    users = await get_channel_users(channel)
    return [user for user in users if user.status == "online"]


async def get_channel_users(channel: Channel) -> List[User]:
    user_ids = set()
    if channel.kind == "dm":
        for member in channel.members:
            user_ids.add(member.pk)
    elif channel.kind == "server":
        members = await get_items(filters={"server": channel.server.pk}, result_obj=ServerMember, limit=None)
        for member in members:
            user_ids.add(member.user.pk)

    users = await get_items(filters={"_id": {"$in": list(user_ids)}}, result_obj=User, limit=None)

    return users


async def fetch_and_cache_channel(channel_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not channel_id:
        return None

    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)
    if not channel:
        return None

    dict_channel = {
        "kind": channel.kind,
    }

    if channel.kind == "dm":
        dict_channel["members"] = ",".join([str(member.pk) for member in channel.members])

    if channel.kind == "server":
        dict_channel["server"] = str(channel.server.pk)

    channel_overwrites = {str(overwrite.role.pk): overwrite.permissions for overwrite in channel.permission_overwrites}
    dict_channel["permissions"] = json.dumps(channel_overwrites)

    await cache.client.hset(f"channel:{channel_id}", mapping=dict_channel)
    return dict_channel
