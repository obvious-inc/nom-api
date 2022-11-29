from typing import Callable

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.app import App
from app.models.channel import Channel
from app.models.server import Server
from app.models.user import User
from app.models.webhook import Webhook
from app.services.crud import get_item_by_id


class TestAppsRoutes:
    @pytest.mark.asyncio
    async def test_create_app_webhook(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        integration_app: App,
    ):
        webhook_data = {"channel": str(server_channel.pk)}
        response = await authorized_client.post(f"/apps/{str(integration_app.pk)}/webhooks", json=webhook_data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert json_response["channel"] == webhook_data["channel"]
        assert json_response["app"] == str(integration_app.pk)
        assert "secret" in json_response  # first time creating webhook, must send secret in response

        webhook_item = await get_item_by_id(id_=json_response["id"], result_obj=Webhook)
        assert webhook_item.secret is not None

    @pytest.mark.asyncio
    async def test_create_app_webhook_as_guest_fails(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        integration_app: App,
        guest_user: User,
        get_authorized_client: Callable,
    ):
        guest_client = await get_authorized_client(guest_user)
        webhook_data = {"channel": str(server_channel.pk)}
        response = await guest_client.post(f"/apps/{str(integration_app.pk)}/webhooks", json=webhook_data)
        assert response.status_code == 403
