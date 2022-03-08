from typing import List

from app.models.server import Server, ServerMember
from app.models.user import User
from app.services.crud import get_items


async def get_server_users(server: Server) -> List[User]:
    members = await get_items(filters={"server": server.pk}, result_obj=ServerMember, current_user=None)
    users = [await member.user.fetch() for member in members]
    return users
