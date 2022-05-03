import functools
from enum import Enum
from typing import List

from bson import ObjectId

from app.models.channel import Channel
from app.models.server import Server, ServerMember
from app.models.user import User
from app.services.crud import get_item


class Permission(Enum):
    MESSAGES_CREATE = "messages.create"
    MESSAGES_LIST = "messages.list"

    MEMBERS_KICK = "members.kick"


ALL_PERMISSIONS = [p for p in Permission]


class APIPermissionError(Exception):
    def __init__(self, needed_permissions: List[Permission], user_permissions: List[Permission]):
        self.needed_permissions = needed_permissions
        self.user_permissions = user_permissions
        self.message = (
            f"needed: [{', '.join([p.value for p in self.needed_permissions])}] | "
            f"user: [{', '.join([p.value for p in self.user_permissions])}]"
        )
        super().__init__(self.message)


async def fetch_base_permissions(user: User, server: Server = None) -> List[Permission]:
    permissions = []

    if server and server.owner == user:
        return ALL_PERMISSIONS

    return permissions


async def fetch_user_permissions(user: User, channel: Channel = None) -> List[Permission]:
    user_permissions = await fetch_base_permissions(user)

    # TODO: Check specific channel or section overrides

    return user_permissions


def needs(permissions):
    def decorator_needs(func):
        @functools.wraps(func)
        async def wrapper_needs(*args, **kwargs):
            current_user = kwargs.get("current_user", None)  # type: User
            if not current_user:
                raise Exception("missing current_user from method")

            # TODO: cache values
            user_permissions = await fetch_user_permissions(user=current_user)

            if not all([req_permission in user_permissions for req_permission in permissions]):
                raise APIPermissionError(needed_permissions=permissions, user_permissions=user_permissions)

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
