import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.user import User


class TestWebsocketRoutes:
    @pytest.mark.asyncio
    async def test_websocket_auth_no_provider_nok(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
    ):
        form_data = {}
        response = await authorized_client.post("/websockets/auth", data=form_data)
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
