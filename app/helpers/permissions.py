import functools
import logging
from enum import Enum
from typing import List

from bson import ObjectId

from app.models.channel import Channel
from app.models.server import Server, ServerMember
from app.models.user import User
from app.services.crud import get_item, get_item_by_id

logger = logging.getLogger(__name__)


class Permission(Enum):
    MESSAGES_CREATE = "messages.create"
    MESSAGES_LIST = "messages.list"

    CHANNELS_CREATE = "channels.create"

    MEMBERS_KICK = "members.kick"


ALL_PERMISSIONS = [p.value for p in Permission]

DEFAULT_ROLE_PERMISSIONS = [
    p.value
    for p in [
        Permission.MESSAGES_LIST,
        Permission.MESSAGES_CREATE,
    ]
]

DEFAULT_DM_PERMISSIONS = [
    p.value
    for p in [
        Permission.MESSAGES_LIST,
        Permission.MESSAGES_CREATE,
    ]
]


class APIPermissionError(Exception):
    def __init__(self, needed_permissions: List[str], user_permissions: List[str]):
        self.needed_permissions = needed_permissions
        self.user_permissions = user_permissions
        self.message = f"needed: {needed_permissions} | user: {user_permissions}"

        super().__init__(self.message)


async def has_permissions(nperms: List[str], uperms: dict, overwrites: dict = None):
    if overwrites:
        ow_roles = list(uperms.keys() & overwrites.keys())
        for r in ow_roles:
            uperms[r] = list(set(uperms[r]) & set(overwrites[r]))

    all_uperms = []
    for role, permissions in uperms.items():
        all_uperms.extend(permissions)
    all_uperms = list(set(all_uperms))

    return all([req_permission in all_uperms for req_permission in nperms])


async def fetch_base_permissions(user: User, server: Server) -> List[str]:
    permissions = []

    if server.owner == user:
        logger.debug("server owner has all permissions")
        return ALL_PERMISSIONS

    # TODO: add admin flag with specific permission overwrite

    member = await get_item(filters={"server": server.pk, "user": user.pk}, result_obj=ServerMember, current_user=user)
    if not member:
        logger.warning("user (%s) doesn't belong to server (%s)", str(user.pk), str(server.pk))
        return []

    roles = [await role.fetch() for role in member.roles]
    for role in roles:
        logger.debug("extending permissions w/ role: %s (%s)", role.name, str(role.pk))
        permissions.extend(role.permissions)

    # remove duplicates
    permissions = list(set(permissions))

    return permissions


async def fetch_user_permissions(user: User, channel_id: str = None, server_id: str = None) -> List[str]:
    if channel_id:
        channel = await get_item_by_id(id_=channel_id, result_obj=Channel, current_user=user)
        if not channel.server:
            logger.warning("ignoring complex permission checks for DMs")
            return DEFAULT_DM_PERMISSIONS
        server = await channel.server.fetch()
    elif server_id:
        server = await get_item_by_id(id_=server_id, result_obj=Server, current_user=user)
    else:
        raise Exception("missing channel_id or server_id from data")

    user_permissions = await fetch_base_permissions(user, server=server)

    # TODO: Check specific channel or section overrides

    return user_permissions


def needs(permissions):
    def decorator_needs(func):
        @functools.wraps(func)
        async def wrapper_needs(*args, **kwargs):
            str_permissions = [p.value for p in permissions]

            current_user = kwargs.get("current_user", None)  # type: User
            if not current_user:
                raise Exception(f"missing current_user from method. args: {args} | kwargs: {kwargs}")

            # TODO: cache and reuse values

            # Extract channel and server from args & kwargs
            channel_id = kwargs.get("channel_id")
            server_id = None

            channel_model = kwargs.get("channel_model")
            if channel_model:
                server_id = str(channel_model.server)

            message_model = kwargs.get("message_model")
            if message_model:
                channel_id = str(message_model.channel)

            if not channel_id and not server_id:
                raise Exception("no channel and server found")

            user_permissions = await fetch_user_permissions(
                user=current_user, channel_id=channel_id, server_id=server_id
            )
            logger.debug("user permissions: %s", user_permissions)

            if not all([req_permission in user_permissions for req_permission in str_permissions]):
                raise APIPermissionError(needed_permissions=str_permissions, user_permissions=user_permissions)

            value = await func(*args, **kwargs)
            return value

        return wrapper_needs

    return decorator_needs


async def user_belongs_to_server(user: User, server_id: str):
    server_member = await get_item(
        filters={"server": ObjectId(server_id), "user": user.id},
        result_obj=ServerMember,
        current_user=user,
    )

    return server_member is not None
