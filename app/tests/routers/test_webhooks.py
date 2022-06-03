import asyncio
import hashlib
import hmac
import json
import random
import string
import time

import arrow
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.config import get_settings
from app.models.app import App
from app.models.message import Message
from app.models.user import User
from app.models.webhook import Webhook
from app.services.crud import get_items


class TestWebhookRoutes:
    @pytest.mark.asyncio
    async def test_pusher_channel_occupied(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
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
        await asyncio.sleep(random.random())
        await current_user.reload()
        assert current_user.online_channels == [channel_id]

    @pytest.mark.asyncio
    async def test_pusher_channel_vacated(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
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
        await asyncio.sleep(random.random())
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

    @pytest.mark.asyncio
    async def test_pusher_status_online(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        settings = get_settings()

        assert current_user.online_channels == []
        assert current_user.status == "offline"

        channel_id = f"private-{str(current_user.id)}"
        current_time = time.time() * 1000
        json_data = {"time_ms": current_time, "events": [{"channel": channel_id, "name": "channel_occupied"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        response = await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        assert response.status_code == 200
        await asyncio.sleep(random.random())
        await current_user.reload()
        assert current_user.online_channels == [channel_id]
        assert current_user.status == "online"

    @pytest.mark.asyncio
    async def test_pusher_status_offline(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        settings = get_settings()

        assert current_user.online_channels == []
        assert current_user.status == "offline"

        channel_id = f"private-{str(current_user.id)}"
        current_time = time.time() * 1000
        json_data = {"time_ms": current_time, "events": [{"channel": channel_id, "name": "channel_occupied"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        response = await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        assert response.status_code == 200
        await asyncio.sleep(random.random())
        await current_user.reload()
        assert current_user.online_channels == [channel_id]
        assert current_user.status == "online"

        current_time = time.time() * 1000
        json_data = {"time_ms": current_time, "events": [{"channel": channel_id, "name": "channel_vacated"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        response = await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        assert response.status_code == 200
        await asyncio.sleep(random.random())
        await current_user.reload()
        assert current_user.online_channels == []
        assert current_user.status == "offline"

    @pytest.mark.asyncio
    async def test_pusher_multiple_channels_online(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        settings = get_settings()

        assert current_user.online_channels == []
        assert current_user.status == "offline"

        def _get_random_channel_name(user_id: str):
            random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            return f"private-{str(current_user.id)}-{random_str}"

        channel1_id = _get_random_channel_name(str(current_user.id))
        current_time = time.time() * 1000
        json_data = {"time_ms": current_time, "events": [{"channel": channel1_id, "name": "channel_occupied"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        response = await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        assert response.status_code == 200
        await asyncio.sleep(random.random())
        await current_user.reload()
        assert current_user.online_channels == [channel1_id]
        assert current_user.status == "online"

        channel2_id = _get_random_channel_name(str(current_user.id))
        current_time = time.time() * 1000
        json_data = {"time_ms": current_time, "events": [{"channel": channel2_id, "name": "channel_occupied"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        response = await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        assert response.status_code == 200
        await asyncio.sleep(random.random())
        await current_user.reload()
        assert current_user.online_channels == [channel1_id, channel2_id]
        assert current_user.status == "online"

    @pytest.mark.asyncio
    async def test_pusher_multiple_channels_not_offline(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        settings = get_settings()

        assert current_user.online_channels == []
        assert current_user.status == "offline"

        def _get_random_channel_name(user_id: str):
            random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            return f"private-{str(current_user.id)}-{random_str}"

        channel1_id = _get_random_channel_name(str(current_user.id))
        current_time = time.time() * 1000
        json_data = {"time_ms": current_time, "events": [{"channel": channel1_id, "name": "channel_occupied"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        response = await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        assert response.status_code == 200
        await asyncio.sleep(random.random())
        await current_user.reload()
        assert current_user.online_channels == [channel1_id]
        assert current_user.status == "online"

        channel2_id = _get_random_channel_name(str(current_user.id))
        current_time = time.time() * 1000
        json_data = {"time_ms": current_time, "events": [{"channel": channel2_id, "name": "channel_occupied"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        response = await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        assert response.status_code == 200
        await asyncio.sleep(random.random())
        await current_user.reload()
        assert current_user.online_channels == [channel1_id, channel2_id]
        assert current_user.status == "online"

        current_time = time.time() * 1000
        json_data = {"time_ms": current_time, "events": [{"channel": channel1_id, "name": "channel_vacated"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        response = await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        assert response.status_code == 200
        await asyncio.sleep(random.random())
        await current_user.reload()
        assert current_user.online_channels == [channel2_id]
        assert current_user.status == "online"

    @pytest.mark.asyncio
    async def test_pusher_multiple_channels_offline(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        settings = get_settings()

        assert current_user.online_channels == []
        assert current_user.status == "offline"

        def _get_random_channel_name(user_id: str):
            random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            return f"private-{str(current_user.id)}-{random_str}"

        channel1_id = _get_random_channel_name(str(current_user.id))
        json_data = {"time_ms": time.time() * 1000, "events": [{"channel": channel1_id, "name": "channel_occupied"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        await asyncio.sleep(random.random())
        await current_user.reload()
        assert current_user.online_channels == [channel1_id]
        assert current_user.status == "online"

        channel2_id = _get_random_channel_name(str(current_user.id))
        json_data = {"time_ms": time.time() * 1000, "events": [{"channel": channel2_id, "name": "channel_occupied"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        await asyncio.sleep(random.random())
        await current_user.reload()
        assert current_user.online_channels == [channel1_id, channel2_id]
        assert current_user.status == "online"

        json_data = {"time_ms": time.time() * 1000, "events": [{"channel": channel1_id, "name": "channel_vacated"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        await asyncio.sleep(random.random())
        await current_user.reload()
        assert current_user.online_channels == [channel2_id]
        assert current_user.status == "online"

        json_data = {"time_ms": time.time() * 1000, "events": [{"channel": channel2_id, "name": "channel_vacated"}]}
        signature = hmac.new(
            settings.pusher_secret.encode("utf8"), json.dumps(json_data).encode("utf8"), hashlib.sha256
        ).hexdigest()
        headers = {"X-Pusher-Key": settings.pusher_key, "X-Pusher-Signature": signature}
        await authorized_client.post("/webhooks/pusher", json=json_data, headers=headers)
        await asyncio.sleep(random.random())
        await current_user.reload()
        assert current_user.online_channels == []
        assert current_user.status == "offline"

    @pytest.mark.asyncio
    async def test_post_webhook_message_ok(
        self,
        app: FastAPI,
        db: Database,
        client,
        current_user: User,
        integration_app: App,
        integration_app_webhook: Webhook,
    ):
        wh_url = f"/webhooks/{str(integration_app_webhook.pk)}/{integration_app_webhook.secret}"
        data = {"blocks": [{"type": "paragraph", "children": [{"text": "New webhook!"}]}]}

        messages = await get_items(filters={}, result_obj=Message)
        assert len(messages) == 0

        response = await client.post(wh_url, json=data)
        assert response.status_code == 200

        messages = await get_items(filters={}, result_obj=Message)
        assert len(messages) == 1
        message = messages[0]
        assert message.type == 2
        assert message.app == integration_app
        assert message.webhook == integration_app_webhook
