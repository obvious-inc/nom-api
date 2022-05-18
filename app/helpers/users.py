import logging
from typing import Any, Dict, List

from bson import ObjectId

from app.exceptions import APIPermissionError
from app.helpers.cache_utils import cache
from app.models.server import ServerMember
from app.services.crud import get_item

logger = logging.getLogger(__name__)


async def get_user_roles_permissions(user: Dict[str, Any], server: Dict[str, Any]) -> Dict[str, List[str]]:
    server_id = server.get("id")
    server_role_ids = user.get(f"{server_id}.roles", "")
    user_roles = server_role_ids.split(",")
    if not user_roles:
        return {}

    server_role_keys = [f"roles.{role_id}" for role_id in user_roles]
    server_roles_permissions = [server.get(key, "") for key in server_role_keys]

    if any([perm is None for perm in server_roles_permissions]):
        raise Exception("unexpected none permission")

    result = {pair[0]: pair[1].split(",") for pair in zip(user_roles, server_roles_permissions)}
    return result


async def fetch_and_cache_user(user_id: str, server_id: str):
    member = await get_item(filters={"server": ObjectId(server_id), "user": ObjectId(user_id)}, result_obj=ServerMember)
    if not member:
        logger.warning("user (%s) doesn't belong to server (%s)", user_id, server_id)
        raise APIPermissionError(message="user does not belong to server")

    member_role_ids = [str(role.pk) for role in member.roles]

    dict_user = {f"{server_id}.roles": ",".join(member_role_ids), "id": user_id}

    await cache.client.hset(f"user:{user_id}", mapping=dict_user)
    return dict_user
