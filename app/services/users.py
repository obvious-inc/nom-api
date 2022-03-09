import http
from typing import Optional, Union

from bson import ObjectId
from fastapi import HTTPException

from app.helpers.queue_utils import queue_bg_task
from app.helpers.w3 import get_wallet_short_name
from app.helpers.ws_events import WebSocketServerEvent
from app.models.base import APIDocument
from app.models.server import ServerMember
from app.models.user import User
from app.schemas.servers import ServerMemberUpdateSchema
from app.schemas.users import UserCreateSchema, UserUpdateSchema
from app.services.crud import get_item, get_item_by_id, update_item
from app.services.websockets import broadcast_server_event, broadcast_user_servers_event


async def create_user(user_model: UserCreateSchema, fetch_ens: bool = False) -> User:
    user = User(**user_model.dict())
    if not user_model.display_name:
        display_name = await get_wallet_short_name(address=user_model.wallet_address, check_ens=fetch_ens)
        user.display_name = display_name
    await user.commit()
    return user


async def get_user_by_wallet_address(wallet_address: str) -> Union[User, APIDocument]:
    user = await get_item(filters={"wallet_address": wallet_address}, result_obj=User)
    return user


async def get_user_by_id(user_id) -> Union[User, APIDocument]:
    return await get_item_by_id(id_=user_id, result_obj=User)


async def get_user_profile_by_server_id(server_id: str, current_user: User) -> Union[ServerMember, APIDocument]:
    profile = await get_item(
        filters={"server": ObjectId(server_id), "user": current_user.pk},
        result_obj=ServerMember,
        current_user=current_user,
    )

    if not profile:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)

    return profile


async def update_user_profile(
    server_id: Optional[str], update_data: Union[UserUpdateSchema, ServerMemberUpdateSchema], current_user: User
) -> Union[ServerMember, User]:
    data = update_data.dict()

    if server_id:
        profile = await get_item(
            filters={"server": ObjectId(server_id), "user": current_user.pk},
            result_obj=ServerMember,
            current_user=current_user,
        )

        if not profile:
            raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)

        updated_item = await update_item(item=profile, data=data)
        await queue_bg_task(
            broadcast_server_event,
            server_id,
            str(current_user.id),
            WebSocketServerEvent.SERVER_PROFILE_UPDATE,
            {**data, "user": str(current_user.id), "member": str(profile.id)},
        )
    else:
        profile = current_user
        updated_item = await update_item(item=profile, data=data)
        await queue_bg_task(
            broadcast_user_servers_event,
            str(current_user.id),
            WebSocketServerEvent.USER_PROFILE_UPDATE,
            {**data, "user": str(current_user.id)},
        )

    return updated_item
