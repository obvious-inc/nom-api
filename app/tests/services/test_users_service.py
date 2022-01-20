import ens
import pytest

from app.schemas.users import UserCreateSchema
from app.services.users import create_user


class TestUsersService:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "wallet_address, expected_display_name",
        [
            ("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "0xd8d...045"),
            ("0x123A6BF26964aF9D7eEd9e03E53415D37aA96456", "0x123...456"),
        ],
    )
    async def test_create_user(self, db, wallet_address, expected_display_name):
        user_model = UserCreateSchema(wallet_address=wallet_address)
        user = await create_user(user_model=user_model)
        assert user is not None
        assert user.wallet_address == wallet_address
        assert user.display_name == expected_display_name

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "wallet_address, expected_display_name",
        [
            ("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "vitalik.eth"),
            ("0xd8da6bf26964af9d7eed9e03e53415d37aa96045", "vitalik.eth"),
            ("0x0000000000000000000000000000000000000000", "0x000...000"),
        ],
    )
    async def test_create_user_resolve_ens(self, db, wallet_address, expected_display_name, monkeypatch):
        user_model = UserCreateSchema(wallet_address=wallet_address)

        def mock_ens_name(cls, address):
            if address.lower() == "0xd8da6bf26964af9d7eed9e03e53415d37aa96045":
                return "vitalik.eth"
            else:
                return None

        monkeypatch.setattr(ens.ENS, "name", mock_ens_name)

        user = await create_user(user_model=user_model, fetch_ens=True)
        assert user is not None
        assert user.wallet_address == wallet_address
        assert user.display_name == expected_display_name

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "wallet_address",
        [
            "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96",
            "0xd8da6bf26964af9d7eed9e03e53415d37aa9604Z",
        ],
    )
    async def test_create_user_invalid_address(self, db, wallet_address):
        user_model = UserCreateSchema(wallet_address=wallet_address)
        with pytest.raises(ValueError):
            await create_user(user_model=user_model)
