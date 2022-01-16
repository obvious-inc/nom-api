from bson import ObjectId

from app.helpers.w3 import get_ens_primary_name_for_address
from app.models.user import User
from app.schemas.users import UserCreateSchema


async def create_user(user_model: UserCreateSchema, expand_ens: bool = False) -> User:
    user = User(**user_model.dict())
    if expand_ens:
        ens_address = await get_ens_primary_name_for_address(user.wallet_address)
        if ens_address:
            user.ens_name = ens_address
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
