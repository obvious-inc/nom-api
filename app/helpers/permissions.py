import functools
import logging
from enum import Enum
from typing import List, Optional, Set

from bson import ObjectId

from app.exceptions import APIPermissionError
from app.models.channel import Channel
from app.models.section import Section
from app.models.server import Server, ServerMember
from app.models.user import User
from app.services.crud import get_item, get_item_by_id

logger = logging.getLogger(__name__)


class Permission(Enum):
    MESSAGES_CREATE = "messages.create"
    MESSAGES_LIST = "messages.list"

    CHANNELS_CREATE = "channels.create"

    MEMBERS_KICK = "members.kick"


# TODO: Move all of this to a constants file?
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


async def has_permissions(needed_permissions: List[str], user_permissions: dict, overwrites: dict = None):
    if overwrites:
        ow_roles = list(user_permissions.keys() & overwrites.keys())
        for r in ow_roles:
            user_permissions[r] = list(set(user_permissions[r]) & set(overwrites[r]))

    overwritten_user_permissions = []
    for role, permissions in user_permissions.items():
        overwritten_user_permissions.extend(permissions)
    overwritten_user_permissions = list(set(overwritten_user_permissions))

    return all([req_permission in overwritten_user_permissions for req_permission in needed_permissions])


async def fetch_permission_overwrites(channel_id: str = None, user: User = None):
    return []


async def _fetch_channel_from_kwargs(kwargs: dict) -> Optional[str]:
    channel_id = kwargs.get("channel_id")

    message_model = kwargs.get("message_model")
    if message_model and not channel_id:
        channel_id = str(message_model.channel)

    return channel_id


async def _fetch_server_from_kwargs(kwargs: dict) -> Optional[str]:
    server_id = kwargs.get("server_id")

    channel_model = kwargs.get("channel_model")
    if channel_model:
        server_id = str(channel_model.server)

    return server_id


async def calc_permissions(current_user: User, channel_id: Optional[str], server: Server) -> Set[str]:
    user_permissions: Set[str] = set()

    member = await get_item(
        filters={"server": server.pk, "user": current_user.pk},
        result_obj=ServerMember,
        current_user=current_user,
    )
    if not member:
        logger.warning("user (%s) doesn't belong to server (%s)", str(current_user.pk), str(server.pk))
        return user_permissions

    roles = [await role.fetch() for role in member.roles]
    logger.debug("user has roles: %s", [(str(r.pk), r.name) for r in roles])

    # fetch from cache
    channel_overwrites = {}
    section_overwrites = {}

    if channel_id:
        channel = await get_item_by_id(id_=channel_id, result_obj=Channel, current_user=current_user)
        channel_overwrites = {
            overwrite.role.pk: set(overwrite.permissions) for overwrite in channel.permission_overwrites
        }

        section = await get_item(
            filters={"server": server.pk, "channels": ObjectId(channel_id)},
            result_obj=Section,
            current_user=current_user,
        )

        if section:
            section_overwrites = {
                overwrite.role.pk: set(overwrite.permissions) for overwrite in section.permission_overwrites
            }

    logger.debug("section overwrites: %s", section_overwrites)
    logger.debug("channel overwrites: %s", channel_overwrites)

    for role in roles:
        logger.debug("fetching role permissions for: %s (%s)", role.name, str(role.pk))
        role_permissions = set(role.permissions)

        c_permissions = channel_overwrites.get(role.pk)
        if c_permissions is not None:
            user_permissions |= c_permissions
            continue

        s_permissions = section_overwrites.get(role.pk)
        if s_permissions is not None:
            user_permissions |= s_permissions
            continue

        user_permissions |= role_permissions

    return user_permissions


async def fetch_user_permissions(func_kwargs: dict, current_user: User) -> List[str]:
    channel_id = await _fetch_channel_from_kwargs(func_kwargs)
    server_id = await _fetch_server_from_kwargs(func_kwargs)

    if not channel_id and not server_id:
        logger.error("no channel and server found. kwargs: %s", func_kwargs)
        raise Exception(f"no channel and server found in kwargs: {func_kwargs}")

    # 3. fetch relevant data from DB (or cache?)
    if server_id:
        server = await get_item_by_id(id_=server_id, result_obj=Server, current_user=current_user)
    elif channel_id:
        channel = await get_item_by_id(id_=channel_id, result_obj=Channel, current_user=current_user)
        if not channel.server:
            return DEFAULT_DM_PERMISSIONS
        server = await channel.server.fetch()
    else:
        raise Exception("missing channel_id or server_id from data")

    if server.owner == current_user:
        logger.debug("server owner has all permissions")
        return ALL_PERMISSIONS

    # TODO: add admin flag with specific permission overwrite

    # 4. start calculating permissions
    user_permissions = await calc_permissions(current_user=current_user, channel_id=channel_id, server=server)

    return list(user_permissions)


def needs(permissions):
    def decorator_needs(func):
        @functools.wraps(func)
        async def wrapper_needs(*args, **kwargs):
            str_permissions = [p.value for p in permissions]
            logger.debug(f"required permissions: {str_permissions}")

            current_user: User = kwargs.get("current_user", None)
            if not current_user:
                raise Exception(f"missing current_user from method. args: {args} | kwargs: {kwargs}")

            user_permissions = await fetch_user_permissions(func_kwargs=kwargs, current_user=current_user)
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
