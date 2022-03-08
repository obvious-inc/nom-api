from typing import Union

from app.helpers.w3 import get_wallet_short_name
from app.models.base import APIDocument
from app.models.channel import ChannelReadState
from app.models.user import User
from app.schemas.users import UserCreateSchema
from app.services.crud import get_item, get_item_by_id, get_items


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


async def get_user_read_states(current_user: User):
    return await get_items(filters={"user": current_user.pk}, result_obj=ChannelReadState, current_user=current_user)
