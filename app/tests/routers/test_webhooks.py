import asyncio
import hashlib
import hmac
import json
import random
import time

import arrow
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.config import get_settings
from app.models.user import User


class TestWebhookRoutes:
    @pytest.mark.asyncio
    async def test_pusher_channel_occupied(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, event_loop
    ):
        settings = get_settings()
        assert current_user.online_channels == []

        channel_id = f"private-{str(current_user.id)}"
        current_time = time.time() * 1000
        json_data = {"time_ms": current_time, "events": [{"channel": channel_id, "name": "channel_occupied"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        response = await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        assert response.status_code == 200
        await asyncio.sleep(random.random(), loop=event_loop)
        await current_user.reload()
        assert current_user.online_channels == [channel_id]

    @pytest.mark.asyncio
    async def test_pusher_channel_vacated(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, event_loop
    ):
        settings = get_settings()
        channel_id = f"private-{str(current_user.id)}"

        current_user.online_channels = [channel_id]
        await current_user.commit()
        assert current_user.online_channels == [channel_id]

        current_time = time.time() * 1000
        json_data = {"time_ms": current_time, "events": [{"channel": channel_id, "name": "channel_vacated"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        response = await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        assert response.status_code == 200
        await asyncio.sleep(random.random(), loop=event_loop)
        await current_user.reload()
        assert current_user.online_channels == []

    @pytest.mark.asyncio
    async def test_pusher_expired_webhook(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
    ):
        settings = get_settings()
        channel_id = f"private-{str(current_user.id)}"

        current_user.online_channels = [channel_id]
        await current_user.commit()
        assert current_user.online_channels == [channel_id]

        current_time = arrow.utcnow().shift(days=-1).float_timestamp * 1000
        json_data = {"time_ms": current_time, "events": [{"channel": channel_id, "name": "channel_vacated"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        response = await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_pusher_bad_signature(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
    ):
        settings = get_settings()
        channel_id = f"private-{str(current_user.id)}"

        current_user.online_channels = [channel_id]
        await current_user.commit()
        assert current_user.online_channels == [channel_id]

        current_time = time.time() * 1000
        json_data = {"time_ms": current_time, "events": [{"channel": channel_id, "name": "channel_vacated"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": f"{signature}-hack"}
        response = await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_pusher_bad_key(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
    ):
        settings = get_settings()
        channel_id = f"private-{str(current_user.id)}"

        current_user.online_channels = [channel_id]
        await current_user.commit()
        assert current_user.online_channels == [channel_id]

        current_time = time.time() * 1000
        json_data = {"time_ms": current_time, "events": [{"channel": channel_id, "name": "channel_vacated"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": "no-key", "X-Pusher-Signature": signature}
        response = await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        assert response.status_code == 401
