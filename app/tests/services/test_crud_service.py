from datetime import datetime

import pytest

from app.models.user import UserModel
from app.services.crud import create_object


class TestCRUDService:

    @pytest.mark.asyncio
    async def test_create_user_ok(self, db):
        email = "test@test.com"
        model = UserModel(email=email)
        user = await create_object(model=model, db=db, user="")
        assert user is not None
        assert user.get("email") == email
        assert "created_at" in user
        assert isinstance(user.get("created_at"), datetime)
