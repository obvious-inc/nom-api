import random
import string
from datetime import datetime

import arrow
import pytest
from pymongo.database import Database

from app.models.channel import Channel
from app.models.server import Server, ServerMember
from app.models.user import User
from app.schemas.channels import ServerChannelCreateSchema
from app.schemas.servers import ServerCreateSchema
from app.schemas.users import UserCreateSchema
from app.services.crud import create_item, create_items, get_items


class TestCRUDService:
    @pytest.mark.asyncio
    async def test_create_user_ok(self, db: Database):
        wallet_address = "0x123"
        model = UserCreateSchema(wallet_address=wallet_address)
        user = await create_item(item=model, result_obj=User, user_field=None)
        assert user is not None
        assert user.wallet_address == wallet_address

    @pytest.mark.asyncio
    async def test_create_user_fields_ok(self, db: Database):
        wallet_address = "0x1234"
        model = UserCreateSchema(wallet_address=wallet_address)
        created_user = await create_item(item=model, result_obj=User, user_field=None)
        assert created_user is not None
        assert created_user.wallet_address == wallet_address
        assert "created_at" in created_user._fields
        assert created_user.created_at is not None
        assert isinstance(created_user.created_at, datetime)
        created_date = arrow.get(created_user.created_at)
        assert created_date is not None
        assert (arrow.utcnow() - created_date).seconds <= 2

    @pytest.mark.asyncio
    async def test_create_item_custom_user_field(self, db: Database, current_user: User):
        server_name = "Verbs DAO"
        server_model = ServerCreateSchema(name=server_name)
        created_server = await create_item(
            item=server_model, result_obj=Server, current_user=current_user, user_field="owner"
        )
        assert created_server is not None
        assert created_server.name == server_name
        assert "owner" in created_server._fields
        assert created_server.owner is not None
        assert created_server.owner == current_user

    @pytest.mark.asyncio
    async def test_get_items_with_size(self, db: Database, current_user: User, server: Server):
        members = await get_items(filters={"server": server.pk}, result_obj=ServerMember, current_user=current_user)
        assert members is not None
        assert len(members) == 1

    @pytest.mark.asyncio
    async def test_create_items(self, db: Database, current_user: User, server: Server):
        channels = await get_items(filters={}, result_obj=Channel, current_user=current_user)
        assert len(channels) == 0

        to_create_channels = []
        for _ in range(100):
            name = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
            channel = ServerChannelCreateSchema(server=str(server.pk), name=name)
            to_create_channels.append(channel)

        object_ids = await create_items(
            to_create_channels, result_obj=Channel, current_user=current_user, user_field="owner"
        )
        assert len(object_ids) == 100

        channels = await get_items(filters={}, result_obj=Channel, current_user=current_user)
        assert len(channels) == 100
