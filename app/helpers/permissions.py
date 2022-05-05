import functools
import logging
from enum import Enum
from typing import List

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


async def fetch_permission_overwrites(channel_id: str = None, user: User = None):
    return []


async def full_handle_permissions(func_args, func_kwargs, req_permissions):
    permissions = [p.value for p in req_permissions]
    logger.debug(f"required permissions: {permissions}")

    # TODO: cache and reuse permission results

    current_user = func_kwargs.get("current_user", None)  # type: User
    if not current_user:
        raise Exception(f"missing current_user from method. args: {func_args} | kwargs: {func_kwargs}")

    channel_id = func_kwargs.get("channel_id")
    server_id = None

    channel_model = func_kwargs.get("channel_model")
    if channel_model:
        server_id = str(channel_model.server)

    message_model = func_kwargs.get("message_model")
    if message_model and not channel_id:
        channel_id = str(message_model.channel)

    if not channel_id and not server_id:
        raise Exception(f"no channel and server found in kwargs: {func_kwargs}")

    if server_id:
        server = await get_item_by_id(id_=server_id, result_obj=Server, current_user=current_user)
    elif channel_id:
        channel = await get_item_by_id(id_=channel_id, result_obj=Channel, current_user=current_user)
        if not channel.server:
            logger.warning("ignoring complex permission checks for DMs")
            return DEFAULT_DM_PERMISSIONS
        server = await channel.server.fetch()
    else:
        raise Exception("missing channel_id or server_id from data")

    # user_permissions = await fetch_base_permissions(user=current_user, server=server)
    user_permissions = set()

    if server.owner == current_user:
        logger.debug("server owner has all permissions")
        return

    # TODO: add admin flag with specific permission overwrite

    member = await get_item(
        filters={"server": server.pk, "user": current_user.pk}, result_obj=ServerMember, current_user=current_user
    )
    if not member:
        logger.warning("user (%s) doesn't belong to server (%s)", str(current_user.pk), str(server.pk))
        raise APIPermissionError(needed_permissions=permissions, user_permissions=list(user_permissions))

    if not channel_id and server:
        # TODO: later, admins should be able to do some actions without channel (channels.create, etc.)
        # TODO: refactor this code once everything is divided and conquered
        logger.warning("without channel_id, using server-wide role permissions. ignoring any overwrites.")
        server_wide_user_permissions = await fetch_base_permissions(user=current_user, server=server)
        if not all([req_permission in server_wide_user_permissions for req_permission in permissions]):
            raise APIPermissionError(needed_permissions=permissions, user_permissions=server_wide_user_permissions)
        else:
            return

    channel = await get_item_by_id(id_=channel_id, result_obj=Channel, current_user=current_user)
    section = await get_item(
        filters={"server": server.pk, "channels": ObjectId(channel_id)}, result_obj=Section, current_user=current_user
    )

    section_overwrites = {}
    if section:
        section_overwrites = {
            overwrite.role.pk: set(overwrite.permissions) for overwrite in section.permission_overwrites
        }
    channel_overwrites = {overwrite.role.pk: set(overwrite.permissions) for overwrite in channel.permission_overwrites}

    logger.debug("section overwrites: %s", section_overwrites)
    logger.debug("channel overwrites: %s", channel_overwrites)

    roles = [await role.fetch() for role in member.roles]
    logger.debug("user has roles: %s", [(str(r.pk), r.name) for r in roles])

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

    # remove duplicates
    user_permissions = list(user_permissions)
    logger.debug("user permissions: %s", user_permissions)

    if not all([req_permission in user_permissions for req_permission in permissions]):
        raise APIPermissionError(needed_permissions=permissions, user_permissions=user_permissions)


def needs(permissions):
    def decorator_needs(func):
        @functools.wraps(func)
        async def wrapper_needs(*args, **kwargs):
            await full_handle_permissions(func_args=args, func_kwargs=kwargs, req_permissions=permissions)
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
