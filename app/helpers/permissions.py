import functools
import logging
from enum import Enum
from typing import Dict, List, Optional, Set

from bson import ObjectId
from sentry_sdk import capture_exception

from app.exceptions import APIPermissionError
from app.helpers.channels import fetch_channel_data, fetch_channel_permission_ow
from app.helpers.sections import fetch_section_permission_ow
from app.helpers.servers import is_server_owner
from app.helpers.users import get_user_roles_permissions
from app.models.server import ServerMember
from app.models.user import User
from app.services.crud import get_item

logger = logging.getLogger(__name__)


class Permission(Enum):
    MESSAGES_CREATE = "messages.create"
    MESSAGES_LIST = "messages.list"

    CHANNELS_CREATE = "channels.create"

    MEMBERS_KICK = "members.kick"

    ROLES_LIST = "roles.list"
    ROLES_CREATE = "roles.create"


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


async def _calc_final_permissions(
    user_roles: Dict[str, List[str]], section_overwrites: Dict[str, List[str]], channel_overwrites: Dict[str, List[str]]
) -> Set[str]:
    permissions = set()
    for role_id, role_permissions in user_roles.items():
        c_permissions = channel_overwrites.get(role_id)
        if c_permissions is not None:
            permissions |= set(c_permissions)
            continue

        s_permissions = section_overwrites.get(role_id)
        if s_permissions is not None:
            permissions |= set(s_permissions)
            continue

        permissions |= set(role_permissions)

    return permissions


async def calc_permissions(user: User, channel_id: Optional[str], server_id: str) -> Set[str]:
    user_roles = await get_user_roles_permissions(user=user, server_id=server_id)
    channel_overwrites = await fetch_channel_permission_ow(channel_id=channel_id)
    section_overwrites = await fetch_section_permission_ow(channel_id=channel_id)

    user_permissions = await _calc_final_permissions(
        user_roles=user_roles,
        section_overwrites=section_overwrites,
        channel_overwrites=channel_overwrites,
    )
    return user_permissions


async def fetch_user_permissions(channel_id: Optional[str], server_id: Optional[str], user: User) -> List[str]:
    channel_info = await fetch_channel_data(channel_id=channel_id)

    if channel_info and channel_info.get("kind") == "dm":
        members = channel_info.get("members", []).split(",")
        if str(user.pk) not in members:
            raise APIPermissionError("user is not a member of DM channel")
        return DEFAULT_DM_PERMISSIONS

    if channel_info and not server_id:
        server_id = channel_info.get("server")

    if not server_id:
        raise Exception("need a server_id at this stage!")

    if await is_server_owner(user=user, server_id=server_id):
        return ALL_PERMISSIONS

    # TODO: add admin flag with specific permission overwrite

    user_permissions = await calc_permissions(user=user, channel_id=channel_id, server_id=server_id)
    return list(user_permissions)


def needs(permissions):
    def decorator_needs(func):
        @functools.wraps(func)
        async def wrapper_needs(*args, **kwargs):
            if kwargs.pop("ignore_permissions", False):
                return await func(*args, **kwargs)

            if len(permissions) == 0:
                return await func(*args, **kwargs)

            try:
                str_permissions = [p.value for p in permissions]
            except AttributeError as e:
                logger.error("unrecognized permission in list: %s", permissions)
                capture_exception(e)
                raise e

            current_user: User = kwargs.get("current_user", None)
            if not current_user:
                logger.error("no current user found. args: %s | kwargs: %s", args, kwargs)
                raise Exception(f"missing current_user from method. args: {args} | kwargs: {kwargs}")

            channel_id = await _fetch_channel_from_kwargs(kwargs)
            server_id = await _fetch_server_from_kwargs(kwargs)

            if not channel_id and not server_id:
                logger.error("no channel and server found. kwargs: %s", kwargs)
                raise Exception(f"no channel and server found in kwargs: {kwargs}")

            user_permissions = await fetch_user_permissions(
                user=current_user, channel_id=channel_id, server_id=server_id
            )

            if not all([req_permission in user_permissions for req_permission in str_permissions]):
                raise APIPermissionError(needed_permissions=str_permissions, user_permissions=user_permissions)

            value = await func(*args, **kwargs)
            return value

        return wrapper_needs

    return decorator_needs


# TODO: Deprecate this and use the @needs decorator instead
async def user_belongs_to_server(user: User, server_id: str):
    server_member = await get_item(filters={"server": ObjectId(server_id), "user": user.id}, result_obj=ServerMember)
    return server_member is not None
