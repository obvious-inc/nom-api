import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.channel import Channel
from app.models.message import Message
from app.models.user import User
from app.schemas.messages import MessageCreateSchema
from app.services.crud import create_item
from app.services.websockets import get_ws_online_channels


class TestWebsocketRoutes:
    @pytest.mark.asyncio
    async def test_websocket_auth_no_provider_nok(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
    ):
        response = await authorized_client.post("/websockets/auth")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_websocket_auth_wrong_provider_nok(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
    ):
        form_data = {"provider": "not-pusher"}
        response = await authorized_client.post("/websockets/auth", data=form_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_websocket_auth_pusher_ok(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
    ):
        channel_id = f"private-{str(current_user.id)}"
        socket_id = "134137.34944081"
        form_data = {"provider": "pusher", "channel_name": channel_id, "socket_id": socket_id}
        response = await authorized_client.post("/websockets/auth", data=form_data)
        assert response.status_code == 200
        assert "auth" in response.json()
        assert response.json()["auth"] is not None

    @pytest.mark.asyncio
    async def test_websocket_auth_pusher_suffix_ok(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
    ):
        suffix = "123123"
        channel_id = f"private-{str(current_user.id)}-{suffix}"
        socket_id = "134137.34944081"
        form_data = {"provider": "pusher", "channel_name": channel_id, "socket_id": socket_id}
        response = await authorized_client.post("/websockets/auth", data=form_data)
        assert response.status_code == 200
        assert "auth" in response.json()
        assert response.json()["auth"] is not None

    @pytest.mark.asyncio
    async def test_websocket_get_online_channels(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        topic_channel: Channel,
    ):
        message_model = MessageCreateSchema(content="hey", channel=str(topic_channel.id))
        message = await create_item(
            item=message_model, result_obj=Message, current_user=current_user, user_field="author"
        )

        current_user.online_channels = [f"private-{str(current_user.id)}"]
        await current_user.commit()

        message_channel = await message.channel.fetch()
        channels = await get_ws_online_channels(channel=message_channel)
        assert len(channels) == 1
        channels = await get_ws_online_channels(channel=message_channel)
        assert len(channels) == 1
        channels = await get_ws_online_channels(channel=message_channel)
        assert len(channels) == 1
