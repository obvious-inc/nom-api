from bson import ObjectId

from app.helpers.cache_utils import cache
from app.helpers.permissions import Permission, needs
from app.models.user import Role, User
from app.schemas.users import RoleCreateSchema
from app.services.crud import create_item, get_items


@needs(permissions=[Permission.ROLES_LIST])
async def get_roles(server_id: str, current_user: User):
    return await get_items(filters={"server": ObjectId(server_id)}, result_obj=Role, current_user=current_user)


@needs(permissions=[Permission.ROLES_CREATE])
async def create_role(server_id: str, role_model: RoleCreateSchema, current_user: User):
    role_model.server = server_id
    role = await create_item(role_model, result_obj=Role, current_user=current_user, user_field=None)
    await cache.client.hset(f"server:{server_id}", f"roles.{str(role.pk)}", ",".join(role.permissions))
    return role
