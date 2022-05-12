import functools
import json
import logging
from enum import Enum
from typing import Dict, List, Optional, Set

from bson import ObjectId
from sentry_sdk import capture_exception

from app.exceptions import APIPermissionError
from app.helpers.cache_utils import cache
from app.helpers.channels import fetch_channel_data
from app.models.channel import Channel
from app.models.section import Section
from app.models.server import Server, ServerMember
from app.models.user import Role, User
from app.services.crud import get_item, get_item_by_id, get_items

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


async def get_user_roles(user: User, server_id: str) -> Dict[str, List[str]]:
    cached_user_roles = await cache.client.hget(f"user:{str(user.pk)}", f"{server_id}.roles")

    if not cached_user_roles:
        member = await get_item(filters={"server": ObjectId(server_id), "user": user.pk}, result_obj=ServerMember)
        if not member:
            logger.warning("user (%s) doesn't belong to server (%s)", str(user.pk), server_id)
            raise APIPermissionError(message="user does not belong to server")

        member_role_ids = [str(role.pk) for role in member.roles]
        await cache.client.hset(f"user:{str(user.pk)}", f"{server_id}.roles", ",".join(member_role_ids))
    else:
        member_role_ids = cached_user_roles.split(",")

    if not member_role_ids:
        return {}

    server_role_keys = [f"roles.{role_id}" for role_id in member_role_ids]
    cached_server_roles = await cache.client.hmget(f"server:{server_id}", server_role_keys)

    if any([cached is None for cached in cached_server_roles]):
        db_roles = await get_items(
            filters={"_id": {"$in": [ObjectId(role_id) for role_id in member_role_ids]}},
            result_obj=Role,
            current_user=user,
        )

        mapping = {f"roles.{str(role.pk)}": ",".join(role.permissions) for role in db_roles}
        await cache.client.hset(f"server:{server_id}", mapping=mapping)
        cached_server_roles = await cache.client.hmget(f"server:{server_id}", server_role_keys)

    result = {pair[0]: pair[1].split(",") for pair in zip(member_role_ids, cached_server_roles)}
    return result


async def _fetch_section_overwrites(channel_id: str) -> Dict[str, List[str]]:
    section_id = await cache.client.hget(f"channel:{channel_id}", "section")
    cached_section_permissions = await cache.client.hget(f"section:{section_id}", "permissions")
    if cached_section_permissions is not None:
        return json.loads(cached_section_permissions)

    section = await get_item(filters={"channels": ObjectId(channel_id)}, result_obj=Section)
    if not section:
        return {}

    section_overwrites = {str(overwrite.role.pk): overwrite.permissions for overwrite in section.permission_overwrites}
    await cache.client.hset(f"section:{str(section.pk)}", "permissions", json.dumps(section_overwrites))
    # TODO: this should be done on creating sections, not here...
    await cache.client.hset(f"channel:{channel_id}", "section", str(section.pk))

    return section_overwrites


async def _fetch_channel_overwrites(channel_id: str) -> Dict[str, List[str]]:
    channel_cache_key = f"channel:{channel_id}"
    cached_channel_permissions = await cache.client.hget(channel_cache_key, "permissions")

    if cached_channel_permissions is not None:
        return json.loads(cached_channel_permissions)

    channel = await get_item_by_id(id_=channel_id, result_obj=Channel)
    channel_overwrites = {str(overwrite.role.pk): overwrite.permissions for overwrite in channel.permission_overwrites}
    await cache.client.hset(channel_cache_key, "permissions", json.dumps(channel_overwrites))
    return channel_overwrites


async def calc_permissions(user: User, channel_id: Optional[str], server_id: str) -> Set[str]:
    roles = await get_user_roles(user=user, server_id=server_id)

    channel_overwrites = {}
    section_overwrites = {}

    if channel_id:
        channel_overwrites = await _fetch_channel_overwrites(channel_id=channel_id)
        section_overwrites = await _fetch_section_overwrites(channel_id=channel_id)

    if channel_overwrites or section_overwrites:
        logger.debug("overwrites. section: %s | channel: %s", section_overwrites, channel_overwrites)

    user_permissions = await _calc_final_permissions(
        user_roles=roles,
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


async def user_belongs_to_server(user: User, server_id: str):
    server_member = await get_item(filters={"server": ObjectId(server_id), "user": user.id}, result_obj=ServerMember)
    return server_member is not None


async def is_server_owner(user: User, server_id: str):
    cached_owner = await cache.client.hget(f"server:{server_id}", "owner")
    if cached_owner:
        return cached_owner == str(user.pk)

    server = await get_item_by_id(id_=server_id, result_obj=Server)
    await cache.client.hset(f"server:{server_id}", "owner", str(server.owner.pk))
    return server.owner == user
