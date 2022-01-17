from datetime import datetime

import arrow
import pytest
from pymongo.database import Database

from app.models.user import User
from app.schemas.users import UserCreateSchema
from app.services.crud import create_item


class TestCRUDService:
    @pytest.mark.asyncio
    async def test_create_user_ok(self, db: Database):
        wallet_address = "0x123"
        model = UserCreateSchema(wallet_address=wallet_address)
        user = await create_item(item=model, result_obj=User, current_user="")
        assert user is not None
        assert user.wallet_address == wallet_address

    @pytest.mark.asyncio
    async def test_create_user_fields_ok(self, db: Database):
        wallet_address = "0x1234"
        model = UserCreateSchema(wallet_address=wallet_address)
        created_user = await create_item(item=model, result_obj=User, current_user="")
        assert created_user is not None
        assert created_user.wallet_address == wallet_address
        assert "created_at" in created_user._fields
        assert created_user.created_at is not None
        assert isinstance(created_user.created_at, datetime)
        created_date = arrow.get(created_user.created_at)
        assert created_date is not None
        assert (arrow.utcnow() - created_date).seconds <= 2
