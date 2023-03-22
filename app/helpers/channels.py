import datetime
import json
import logging
import re
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.helpers.cache_utils import cache
from app.helpers.queue_utils import timed_task
from app.helpers.w3 import checksum_address
from app.models.channel import Channel
from app.models.server import ServerMember
from app.models.user import User
from app.schemas.users import UserCreateSchema
from app.services.crud import create_item, get_item, get_item_by_id, get_items, update_item

logger = logging.getLogger(__name__)


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

    elif channel.kind == "dm" or channel.kind == "topic":
        return user in channel.members

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


async def convert_permission_object_to_cached(channel: Channel) -> str:
    channel_overwrites = {}
    for overwrite in channel.permission_overwrites:
        if overwrite.role:
            channel_overwrites[str(overwrite.role.pk)] = overwrite.permissions
        elif overwrite.group:
            channel_overwrites[str(overwrite.group)] = overwrite.permissions

    return json.dumps(channel_overwrites)


async def fetch_and_cache_channel(channel_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not channel_id:
        return None

    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)
    if not channel:
        return None

    dict_channel = {"kind": channel.kind, "owner": str(channel.owner.pk)}

    if channel.kind == "dm" or channel.kind == "topic":
        dict_channel["members"] = ",".join([str(member.pk) for member in channel.members])

    if channel.kind == "server":
        dict_channel["server"] = str(channel.server.pk)

    dict_channel["permissions"] = await convert_permission_object_to_cached(channel)

    await cache.client.hset(f"channel:{channel_id}", mapping=dict_channel)
    return dict_channel


@timed_task()
async def update_channel_last_message(channel_id, message_created_at: datetime.datetime):
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)
    if not channel.last_message_at or message_created_at > channel.last_message_at:
        await update_item(item=channel, data={"last_message_at": message_created_at})


async def parse_member_list(members: List[str], create_if_not_user: bool = True) -> List[User]:
    unique_member_list = list(set(members))

    user_ids = [ObjectId(member) for member in unique_member_list if ObjectId.is_valid(member)]
    users = await get_items(filters={"_id": {"$in": user_ids}}, result_obj=User, limit=None)

    addresses = [checksum_address(member) for member in unique_member_list if re.match(r"^0x[a-fA-F\d]{40}$", member)]
    address_users = await get_items(filters={"wallet_address": {"$in": addresses}}, result_obj=User, limit=None)
    users.extend(address_users)

    if create_if_not_user:
        existing_wallets = [user.wallet_address for user in users]
        new_wallets = [wallet for wallet in addresses if wallet not in existing_wallets]

        for address in new_wallets:
            wallet_addr = checksum_address(address)
            user = await create_item(
                item=UserCreateSchema(wallet_address=wallet_addr), result_obj=User, user_field=None
            )
            users.append(user)

    return users
