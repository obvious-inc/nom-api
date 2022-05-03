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

    MEMBERS_KICK = "members.kick"


ALL_PERMISSIONS = [p.value for p in Permission]
DEFAULT_ROLE_PERMISSIONS = [
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


async def fetch_base_permissions(user: User, server: Server) -> List[str]:
    permissions = []

    if server.owner == user:
        logger.debug("server owner has all permissions")
        return ALL_PERMISSIONS

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


async def fetch_user_permissions(user: User, channel_id: str) -> List[str]:
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel, current_user=user)

    if not channel.server:
        logger.warning("ignoring complex permission checks for DMs")
        return []

    server = await channel.server.fetch()

    user_permissions = await fetch_base_permissions(user, server=server)

    # TODO: Check specific channel or section overrides

    return user_permissions


def needs(permissions):
    def decorator_needs(func):
        @functools.wraps(func)
        async def wrapper_needs(*args, **kwargs):
            current_user = kwargs.get("current_user", None)  # type: User
            if not current_user:
                raise Exception(f"missing current_user from method. args: {args} | kwargs: {kwargs}")

            str_permissions = [p.value for p in permissions]

            # TODO: cache and reuse values

            channel_id = kwargs.get("channel_id")

            user_permissions = await fetch_user_permissions(user=current_user, channel_id=channel_id)
            print("user permissions", user_permissions)

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
