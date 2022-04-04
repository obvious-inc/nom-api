import pytest
from pymongo.database import Database

from app.helpers.channels import is_user_in_channel
from app.models.channel import Channel
from app.models.user import User


class TestChannelHelper:
    @pytest.mark.asyncio
    async def test_is_user_in_dm_channel_ok(self, db: Database, current_user: User, dm_channel: Channel):
        assert await is_user_in_channel(current_user, dm_channel) is True

    @pytest.mark.asyncio
    async def test_is_user_in_server_channel_ok(self, db: Database, current_user: User, server_channel: Channel):
        assert await is_user_in_channel(current_user, server_channel) is True

    @pytest.mark.asyncio
    async def test_is_user_in_server_channel_fail(
        self, db: Database, current_user: User, server_channel: Channel, guest_user: User
    ):
        assert await is_user_in_channel(guest_user, server_channel) is False

    @pytest.mark.asyncio
    async def test_is_user_in_dm_channel_fail(
        self, db: Database, current_user: User, dm_channel: Channel, guest_user: User
    ):
        assert await is_user_in_channel(guest_user, dm_channel) is False
