from bson import ObjectId

from app.models.server import ServerMember
from app.models.user import User
from app.services.crud import get_item

# this file will become more dynamic with time


async def user_belongs_to_server(user: User, server_id: str):
    server_member = await get_item(
        filters={"server": ObjectId(server_id), "user": user.id},
        result_obj=ServerMember,
        current_user=user,
    )

    return server_member is not None
