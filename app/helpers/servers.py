from typing import List

from bson import ObjectId

from app.helpers.cache_utils import cache
from app.models.server import Server
from app.models.user import Role, User
from app.services.crud import get_item_by_id, get_items


async def get_server_roles_permissions(role_ids: List[str], server_id: str):
    server_role_keys = [f"roles.{role_id}" for role_id in role_ids]
    server_roles_permissions = await cache.client.hmget(f"server:{server_id}", server_role_keys)

    if all([cached is not None for cached in server_roles_permissions]):
        return server_roles_permissions

    db_roles = await get_items(
        filters={"_id": {"$in": [ObjectId(role_id) for role_id in role_ids]}},
        result_obj=Role,
        current_user=None,
    )

    mapping = {f"roles.{str(role.pk)}": ",".join(role.permissions) for role in db_roles}
    await cache.client.hset(f"server:{server_id}", mapping=mapping)

    server_roles_permissions = await cache.client.hmget(f"server:{server_id}", server_role_keys)
    return server_roles_permissions


async def is_server_owner(user: User, server_id: str):
    cached_owner = await cache.client.hget(f"server:{server_id}", "owner")
    if cached_owner:
        return cached_owner == str(user.pk)

    server = await get_item_by_id(id_=server_id, result_obj=Server)
    await cache.client.hset(f"server:{server_id}", "owner", str(server.owner.pk))
    return server.owner == user
