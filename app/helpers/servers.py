from bson import ObjectId

from app.helpers.cache_utils import cache
from app.models.server import Server
from app.models.user import Role
from app.services.crud import get_item_by_id, get_items


async def fetch_and_cache_server(server_id: str):
    if not server_id:
        return {}

    server = await get_item_by_id(id_=server_id, result_obj=Server)
    if not server:
        return {}

    server_roles = await get_items(
        filters={"server": ObjectId(server_id)},
        result_obj=Role,
        current_user=None,
    )
    dict_server = {f"roles.{str(role.pk)}": ",".join(role.permissions) for role in server_roles}

    dict_server["owner"] = str(server.owner.pk)
    dict_server["id"] = server_id

    await cache.client.hset(f"server:{server_id}", mapping=dict_server)
    return dict_server
