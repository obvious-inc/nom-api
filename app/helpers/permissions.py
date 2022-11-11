import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

from bson import ObjectId
from fastapi import HTTPException
from starlette.requests import Request

from app.constants.permissions import (
    ALL_PERMISSIONS,
    CHANNEL_OWNER_PERMISSIONS,
    DEFAULT_DM_MEMBER_PERMISSIONS,
    DEFAULT_TOPIC_MEMBER_PERMISSIONS,
    DEFAULT_USER_PERMISSIONS,
    MEMBERS_GROUP,
    OWNERS_GROUP,
    PUBLIC_GROUP,
    SERVER_OWNER_PERMISSIONS,
)
from app.exceptions import APIPermissionError
from app.helpers.apps import fetch_and_cache_app
from app.helpers.cache_utils import cache, convert_redis_list_to_dict
from app.helpers.channels import fetch_and_cache_channel
from app.helpers.sections import fetch_and_cache_section
from app.helpers.servers import fetch_and_cache_server
from app.helpers.users import fetch_and_cache_user, get_user_roles_permissions
from app.models.app import App
from app.models.channel import Channel
from app.models.server import Server, ServerMember
from app.models.user import User
from app.services.crud import get_item

logger = logging.getLogger(__name__)


async def _fetch_fields_from_request_body(fields: List[str], request: Request) -> Optional[str]:
    try:
        body = await request.json()
    except Exception as e:
        body = await request.body()
        if body == b"":
            return None
        logger.warning(f"issue decoding json body: {e}")
        return None

    if not body:
        return None

    if isinstance(body, dict):
        for field in fields:
            value = body.get(field)
            if value:
                return value

    return None


async def _fetch_channel_from_request(request: Request) -> Optional[str]:
    request_path = request.url.path
    channel_matches = re.findall(r"^/channels/(.{24})/?", request_path)
    if channel_matches:
        return channel_matches[0]

    value = await _fetch_fields_from_request_body(fields=["channel", "channel_id"], request=request)
    if value:
        return value

    return None


async def _fetch_server_from_request(request: Request) -> Optional[str]:
    request_path = request.url.path
    server_matches = re.findall(r"^/servers/(.{24})/?", request_path)
    if server_matches:
        return server_matches[0]

    value = await _fetch_fields_from_request_body(fields=["server", "server_id"], request=request)
    if value:
        return value

    return None


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

    permissions |= set(channel_overwrites.get(PUBLIC_GROUP, []))

    return permissions


async def fetch_cached_permissions_data(channel_id: Optional[str], user_id: str, app_id: str):
    lua_script = """
        local channel_data = redis.call('HGETALL', KEYS[1])
        local user_data
        local app_data
        if KEYS[2] then
            user_data = redis.call('HGETALL', KEYS[2])
        else
            user_data = {}
        end
        if KEYS[3] then
            app_data = redis.call('HGETALL', KEYS[3])
        else
            app_data = {}
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

        return { channel_data, user_data, server_data, section_data, app_data }
        """
    fetch_cached_data = cache.client.register_script(lua_script)
    channel, user, server, section, app = await fetch_cached_data(
        keys=[
            f"channel:{channel_id}",
            f"user:{user_id}" if user_id != "" else user_id,
            f"app:{app_id}" if app_id != "" else app_id,
        ]
    )
    channel_data = await convert_redis_list_to_dict(channel)
    user_data = await convert_redis_list_to_dict(user)
    server_data = await convert_redis_list_to_dict(server)
    section_data = await convert_redis_list_to_dict(section)
    app_data = await convert_redis_list_to_dict(app)
    return channel_data, user_data, server_data, section_data, app_data


async def fetch_user_permissions(
    channel_id: Optional[str],
    server_id: Optional[str],
    user_id: Optional[str],
    app_id: Optional[str] = None,
    token_scopes: Optional[List[str]] = None,
) -> List[str]:
    logger.debug(f"fetching permissions. user: {user_id} | channel: {channel_id} | server: {server_id} | app: {app_id}")
    if not channel_id and not server_id:
        return DEFAULT_USER_PERMISSIONS

    channel, user, server, section, app = await fetch_cached_permissions_data(
        channel_id=channel_id, user_id=user_id or "", app_id=app_id or ""
    )

    user_roles = {}

    if channel_id:
        if not channel or "kind" not in channel:
            channel = await fetch_and_cache_channel(channel_id=channel_id)

        if not channel:
            raise HTTPException(status_code=404, detail="channel not found")

        if channel.get("kind") == "dm":
            members = channel.get("members", []).split(",")
            if not user_id or user_id not in members:
                raise APIPermissionError("user is not a member of DM channel")
            return DEFAULT_DM_MEMBER_PERMISSIONS
        elif channel.get("kind") == "topic":
            channel_perms = json.loads(channel.get("permissions", ""))
            if user_id and channel.get("owner") == user_id:
                owner_perms = channel_perms.get(OWNERS_GROUP, [])
                if not owner_perms:
                    return CHANNEL_OWNER_PERMISSIONS

                user_roles[OWNERS_GROUP] = owner_perms

            members = channel.get("members", []).split(",")
            if user_id and user_id in members:
                member_perms = channel_perms.get(MEMBERS_GROUP, [])
                if member_perms:
                    user_roles[MEMBERS_GROUP] = member_perms
                else:
                    user_roles[MEMBERS_GROUP] = DEFAULT_TOPIC_MEMBER_PERMISSIONS

            if app_id:
                if not app:
                    app = await fetch_and_cache_app(app_id)

                app_channels = app.get("channels", "").split(",")
                if channel_id not in app_channels:
                    raise APIPermissionError("app is not authorized to access this channel")

                # TODO: revisit this once apps can have access to servers or DMs
                if token_scopes:
                    return token_scopes
                else:
                    return app.get(f"channel:{channel_id}", "").split(",")

        elif channel.get("kind") == "server":
            server_id = channel.get("server")
        else:
            raise APIPermissionError(f"unknown channel type: {channel}")

    if server_id and not server:
        server = await fetch_and_cache_server(server_id=server_id)
        if user_id and server.get("owner") == user_id:
            return SERVER_OWNER_PERMISSIONS
        # TODO: add admin flag with specific permission overwrite

    if server and user_id:
        if not user or not user.get(f"{server_id}.roles", None):
            user = await fetch_and_cache_user(user_id=user_id, server_id=server_id)

        user_roles = await get_user_roles_permissions(user=user, server=server)

    section_overwrites = {}
    channel_overwrites = json.loads(channel.get("permissions", "{}"))
    if not section and channel_id:
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

    return sorted(list(user_permissions))


async def validate_resource_permission(user: User, action: str, resource: Any) -> None:
    user_id = str(user.pk)

    channel_id = None
    server_id = None

    resource_id = str(resource.pk)
    if isinstance(resource, Channel):
        channel_id = resource_id
    elif isinstance(resource, Server):
        server_id = resource_id
    else:
        raise Exception("unexpected resource: {}".format(resource))

    user_permissions = await fetch_user_permissions(user_id=user_id, channel_id=channel_id, server_id=server_id)

    if action not in user_permissions:
        raise APIPermissionError(needed_permissions=[action], user_permissions=user_permissions)


async def check_request_permissions(
    request: Request, permissions: List[str], current_user: Optional[User] = None, current_app: Optional[App] = None
):
    channel_id = await _fetch_channel_from_request(request=request)
    server_id = await _fetch_server_from_request(request=request)
    user_id = str(current_user.pk) if current_user else None
    app_id = str(current_app.pk) if current_app else None

    try:
        token_scopes = request.state.scopes
    except AttributeError:
        token_scopes = []

    user_permissions = await fetch_user_permissions(
        user_id=user_id, channel_id=channel_id, server_id=server_id, app_id=app_id, token_scopes=token_scopes
    )

    request.state.permissions_used = ",".join(permissions)

    if not all([req_permission in user_permissions for req_permission in permissions]):
        raise APIPermissionError(needed_permissions=permissions, user_permissions=user_permissions)


# TODO: Deprecate this and use the @needs decorator instead
async def user_belongs_to_server(user: User, server_id: str):
    server_member = await get_item(filters={"server": ObjectId(server_id), "user": user.id}, result_obj=ServerMember)
    return server_member is not None


async def validate_oauth_request_scope_str(scope: Optional[str]) -> List[str]:
    if not scope:
        return []

    request_scopes = scope.split(" ")
    if any([request_scope not in ALL_PERMISSIONS for request_scope in request_scopes]):
        raise Exception(f"unexpected scope in request: {scope}")

    return request_scopes
