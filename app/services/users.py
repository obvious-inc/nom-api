from bson import ObjectId

from app.helpers.w3 import get_wallet_short_name
from app.models.user import User
from app.schemas.users import UserCreateSchema


async def create_user(user_model: UserCreateSchema, fetch_ens: bool = False) -> User:
    user = User(**user_model.dict())
    if not user_model.display_name:
        display_name = await get_wallet_short_name(address=user_model.wallet_address, check_ens=fetch_ens)
        user.display_name = display_name
    await user.commit()
    return user


async def get_user_by_wallet_address(wallet_address: str) -> User:
    user = await User.find_one({"wallet_address": wallet_address})
    return user


async def get_user_by_id(user_id) -> User:
    if isinstance(user_id, str):
        user_id = ObjectId(user_id)
    elif isinstance(user_id, ObjectId):
        pass
    else:
        raise Exception(f"unexpected user_id type: {type(user_id)}")

    return await User.find_one({"_id": user_id})
