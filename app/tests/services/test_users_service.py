import pytest

from app.schemas.users import UserCreateSchema
from app.services.users import create_user


class TestUsersService:
    @pytest.mark.asyncio
    async def test_create_user(self, db):
        wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        user_model = UserCreateSchema(wallet_address=wallet_address)
        user = await create_user(user_model=user_model)

        assert user is not None
        assert user.wallet_address == wallet_address
        assert user.ens_name is None
        assert user.email is None

    @pytest.mark.skip
    async def test_create_user_expand_ens(self, db):
        wallet_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        user_model = UserCreateSchema(wallet_address=wallet_address)
        user = await create_user(user_model=user_model, expand_ens=True)

        assert user is not None
        assert user.wallet_address == wallet_address
        assert user.email is None
        assert user.ens_name is not None

        # TODO: replace all tests and wallet addresses w/ test wallet. This is just for fun
        assert user.ens_name == "vitalik.eth"
