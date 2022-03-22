import pytest
from pymongo.database import Database

from app.models.channel import Channel
from app.models.message import Message
from app.models.server import Server
from app.models.user import User


class TestBaseModel:
    @pytest.mark.asyncio
    async def test_to_dict_eq_dumped(self, db: Database, current_user: User):
        assert current_user.dump() == await current_user.to_dict()

    @pytest.mark.asyncio
    async def test_to_dict_exclude_fields_ok(self, db: Database, current_user: User):
        dumped_user = current_user.dump()
        assert "wallet_address" in dumped_user
        to_dict_user = await current_user.to_dict(exclude_fields=["wallet_address"])
        assert "wallet_address" not in to_dict_user

    @pytest.mark.asyncio
    async def test_to_dict_exclude_non_existing_fields_ok(self, db: Database, current_user: User):
        to_dict_user = await current_user.to_dict(exclude_fields=["some_field"])
        assert to_dict_user == current_user.dump()

    @pytest.mark.asyncio
    async def test_to_dict_expand_field_ok(
        self, db: Database, server: Server, server_channel: Channel, channel_message: Message
    ):
        dumped_message = channel_message.dump()
        assert "channel" in dumped_message
        assert isinstance(dumped_message["channel"], str)

        to_dict_message = await channel_message.to_dict(expand_fields=["channel"])
        assert "channel" in to_dict_message
        assert isinstance(to_dict_message["channel"], dict)
        assert dumped_message["channel"] == to_dict_message["channel"]["id"]

    @pytest.mark.asyncio
    async def test_to_dict_expand_non_existing_fields_ok(
        self, db: Database, server: Server, server_channel: Channel, channel_message: Message
    ):
        to_dict_message = await channel_message.to_dict(expand_fields=["random_field"])
        assert to_dict_message == channel_message.dump()

    @pytest.mark.asyncio
    async def test_to_dict_expand_non_reference_fields_ok(
        self, db: Database, server: Server, server_channel: Channel, channel_message: Message
    ):
        to_dict_message = await channel_message.to_dict(expand_fields=["content"])
        assert to_dict_message == channel_message.dump()

    @pytest.mark.asyncio
    async def test_to_dict_ok(self, db: Database, server: Server, server_channel: Channel, channel_message: Message):
        to_dict_message = await channel_message.to_dict()
        assert to_dict_message == channel_message.dump()
