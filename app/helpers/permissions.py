import functools
import json
import logging
import re
from enum import Enum
from typing import Dict, List, Optional, Set

from bson import ObjectId
from sentry_sdk import capture_exception
from starlette.requests import Request

from app.exceptions import APIPermissionError
from app.helpers.cache_utils import cache, convert_redis_list_to_dict
from app.helpers.channels import fetch_and_cache_channel
from app.helpers.sections import fetch_and_cache_section
from app.helpers.servers import fetch_and_cache_server
from app.helpers.users import fetch_and_cache_user, get_user_roles_permissions
from app.models.app import App
from app.models.server import ServerMember
from app.models.user import User
from app.services.crud import get_item

logger = logging.getLogger(__name__)


class Permission(Enum):
    MESSAGES_CREATE = "messages.create"
    MESSAGES_LIST = "messages.list"
    MESSAGES_PUBLIC_LIST = "messages.public.list"

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


async def _fetch_channel_from_request(request: Request) -> Optional[str]:
    request_path = request.url.path
    channel_matches = re.findall(r"^/channels/(.{24})/", request_path)
    if channel_matches:
        return channel_matches[0]

    body = await request.json()
    if not body:
        return None

    for param in ["channel", "channel_id"]:
        if hasattr(body, param):
            return body.get(param)

    return None


async def _fetch_server_from_request(request: Request) -> Optional[str]:
    request_path = request.url.path
    server_matches = re.findall(r"^/servers/(.{24})/", request_path)
    if not server_matches:
        return None

    return server_matches[0]


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


async def fetch_cached_permissions_data(channel_id: Optional[str], user_id: str):
    lua_script = """
        local channel_data = redis.call('HGETALL', KEYS[1])
        local user_data
        if KEYS[2] then
            user_data = redis.call('HGETALL', KEYS[2])
        else
            user_data = {}
        end
        local server_id = redis.call('HGET', KEYS[1], 'server')
        local server_data
        if server_id then
            server_data = redis.call('HGETALL', "server:" .. server_id)
        else
            server_data = {}
        end
        local section_id = redis.call('HGET', KEYS[1], 'section')
        local section_data
        if section_id then
            section_data = redis.call('HGETALL', "section:" .. section_id)
        else
            section_data = {}
        end

        return { channel_data, user_data, server_data, section_data }
        """
    fetch_cached_data = cache.client.register_script(lua_script)
    channel, user, server, section = await fetch_cached_data(
        keys=[f"channel:{channel_id}", f"user:{user_id}" if user_id != "" else user_id]
    )
    channel_data = await convert_redis_list_to_dict(channel)
    user_data = await convert_redis_list_to_dict(user)
    server_data = await convert_redis_list_to_dict(server)
    section_data = await convert_redis_list_to_dict(section)
    return channel_data, user_data, server_data, section_data


async def fetch_user_permissions(
    channel_id: Optional[str], server_id: Optional[str], user_id: Optional[str]
) -> List[str]:
    channel, user, server, section = await fetch_cached_permissions_data(channel_id=channel_id, user_id=user_id or "")

    if not channel:
        channel = await fetch_and_cache_channel(channel_id=channel_id)

    if channel and channel.get("kind") == "dm":
        members = channel.get("members", []).split(",")
        if not user_id or user_id not in members:
            raise APIPermissionError("user is not a member of DM channel")
        return DEFAULT_DM_PERMISSIONS

    if channel and not server_id:
        server_id = channel.get("server")

    if not server_id:
        raise Exception("need a server_id at this stage!")

    if not server:
        server = await fetch_and_cache_server(server_id=server_id)

    if user_id and server.get("owner") == user_id:
        return ALL_PERMISSIONS

    # TODO: add admin flag with specific permission overwrite

    user_roles = {}
    if user_id:
        if not user or not user.get(f"{server_id}.roles", None):
            user = await fetch_and_cache_user(user_id=user_id, server_id=server_id)

        user_roles = await get_user_roles_permissions(user=user, server=server)

    channel_overwrites = {}
    section_overwrites = {}

    if channel_id:
        channel_overwrites = json.loads(channel.get("permissions", {}))
        if not section:
            section_id = channel.get("section")
            if section_id != "":
                section = await fetch_and_cache_section(section_id=section_id, channel_id=channel_id)

        if section:
            section_overwrites = json.loads(section.get("permissions", {}))

    user_permissions = await _calc_final_permissions(
        user_roles=user_roles,
        section_overwrites=section_overwrites,
        channel_overwrites=channel_overwrites,
    )

    if not user_id:
        # TODO: this should only be temporary!
        user_permissions.add("messages.public.list")

    return list(user_permissions)


async def check_request_permissions(request: Request, permissions: List[str], current_user: Optional[User] = None):
    channel_id = await _fetch_channel_from_request(request=request)
    server_id = await _fetch_server_from_request(request=request)

    if not channel_id and not server_id:
        logger.error("no channel and server found for request URL: %s", request.url)
        raise Exception(f"no channel and server found for request: {request.url}")

    user_id = str(current_user.pk) if current_user else None
    user_permissions = await fetch_user_permissions(user_id=user_id, channel_id=channel_id, server_id=server_id)

    if not any([req_permission in user_permissions for req_permission in permissions]):
        raise APIPermissionError(needed_permissions=permissions, user_permissions=user_permissions)


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
            current_app: App = kwargs.get("current_app", None)

            if current_user:
                channel_id = await _fetch_channel_from_kwargs(kwargs)
                server_id = await _fetch_server_from_kwargs(kwargs)

                if not channel_id and not server_id:
                    logger.error("no channel and server found. kwargs: %s", kwargs)
                    raise Exception(f"no channel and server found in kwargs: {kwargs}")

                user_permissions = await fetch_user_permissions(
                    user_id=str(current_user.pk), channel_id=channel_id, server_id=server_id
                )
            elif current_app:
                user_permissions = current_app.permissions
            else:
                logger.error("no current user or app found. args: %s | kwargs: %s", args, kwargs)
                raise Exception(f"missing current_user or app from method. args: {args} | kwargs: {kwargs}")

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
