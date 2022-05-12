import logging
from typing import Dict, List

from bson import ObjectId

from app.exceptions import APIPermissionError
from app.helpers.cache_utils import cache
from app.helpers.servers import get_server_roles_permissions
from app.models.server import ServerMember
from app.models.user import User
from app.services.crud import get_item

logger = logging.getLogger(__name__)


async def get_user_roles_ids(user: User, server_id: str) -> List[str]:
    cached_user_roles = await cache.client.hget(f"user:{str(user.pk)}", f"{server_id}.roles")
    if cached_user_roles:
        return cached_user_roles.split(",")

    member = await get_item(filters={"server": ObjectId(server_id), "user": user.pk}, result_obj=ServerMember)
    if not member:
        logger.warning("user (%s) doesn't belong to server (%s)", str(user.pk), server_id)
        raise APIPermissionError(message="user does not belong to server")

    member_role_ids = [str(role.pk) for role in member.roles]
    await cache.client.hset(f"user:{str(user.pk)}", f"{server_id}.roles", ",".join(member_role_ids))
    return member_role_ids


async def get_user_roles_permissions(user: User, server_id: str) -> Dict[str, List[str]]:
    user_roles = await get_user_roles_ids(user=user, server_id=server_id)
    if not user_roles:
        return {}

    server_roles_permissions = await get_server_roles_permissions(role_ids=user_roles, server_id=server_id)
    result = {pair[0]: pair[1].split(",") for pair in zip(user_roles, server_roles_permissions)}
    return result
