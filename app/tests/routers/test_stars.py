from typing import Callable

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.channel import Channel
from app.models.message import Message
from app.models.server import Server
from app.models.user import User


class TestStarsRoutes:
    @pytest.mark.asyncio
    async def test_create_star_channel_message(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, channel_message: Message
    ):
        data = {"type": "message", "reference": str(channel_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response["type"] == "message"
        assert json_response["reference"] == str(channel_message.id)

    @pytest.mark.asyncio
    async def test_create_star_dm(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, direct_message: Message
    ):
        data = {"type": "message", "reference": str(direct_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response["type"] == "message"
        assert json_response["reference"] == str(direct_message.id)

    @pytest.mark.asyncio
    async def test_create_star_server_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server_channel: Channel
    ):
        data = {"type": "channel", "reference": str(server_channel.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response["type"] == "channel"
        assert json_response["reference"] == str(server_channel.id)

    @pytest.mark.asyncio
    async def test_create_star_dm_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, dm_channel: Channel
    ):
        data = {"type": "channel", "reference": str(dm_channel.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response["type"] == "channel"
        assert json_response["reference"] == str(dm_channel.id)

    @pytest.mark.asyncio
    async def test_create_star_server(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        data = {"type": "server", "reference": str(server.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_star_random(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        data = {"type": "random", "reference": "whatevz"}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_star_multiple_times(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, channel_message: Message
    ):
        data = {"type": "message", "reference": str(channel_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201

        stars = (await authorized_client.get("/stars")).json()
        assert len(stars) == 1

        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 400

        stars = (await authorized_client.get("/stars")).json()
        assert len(stars) == 1

    @pytest.mark.asyncio
    async def test_create_same_star_multiple_users(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        guest_user: User,
        get_authorized_client: Callable,
        channel_message: Message,
    ):
        data = {"type": "message", "reference": str(channel_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201

        stars = (await authorized_client.get("/stars")).json()
        assert len(stars) == 1

        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post("/stars", json=data)
        assert response.status_code == 201

        stars = (await authorized_client.get("/stars")).json()
        assert len(stars) == 1

        guest_stars = (await guest_client.get("/stars")).json()
        assert len(guest_stars) == 1

    @pytest.mark.asyncio
    async def test_list_stars(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, channel_message: Message
    ):
        stars = (await authorized_client.get("/stars")).json()
        assert len(stars) == 0

        data = {"type": "message", "reference": str(channel_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201

        stars = (await authorized_client.get("/stars")).json()

        assert len(stars) == 1
        assert stars[0]["type"] == "message"
        assert stars[0]["reference"] == str(channel_message.id)

    @pytest.mark.asyncio
    async def test_delete_star(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, channel_message: Message
    ):
        data = {"type": "message", "reference": str(channel_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201

        star_id = response.json()["id"]

        response = await authorized_client.delete(f"/stars/{star_id}")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_star_multiple_times(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, channel_message: Message
    ):
        data = {"type": "message", "reference": str(channel_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        star_id = response.json()["id"]

        stars = (await authorized_client.get("/stars")).json()
        assert len(stars) == 1

        response = await authorized_client.delete(f"/stars/{star_id}")
        assert response.status_code == 204

        stars = (await authorized_client.get("/stars")).json()
        assert len(stars) == 0

        response = await authorized_client.delete(f"/stars/{star_id}")
        assert response.status_code == 204

        stars = (await authorized_client.get("/stars")).json()
        assert len(stars) == 0

        response = await authorized_client.delete(f"/stars/{star_id}")
        assert response.status_code == 204

        stars = (await authorized_client.get("/stars")).json()
        assert len(stars) == 0

    @pytest.mark.asyncio
    async def test_delete_other_user_star(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        guest_user: User,
        get_authorized_client: Callable,
        channel_message: Message,
    ):
        data = {"type": "message", "reference": str(channel_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        star_id = response.json()["id"]

        stars = (await authorized_client.get("/stars")).json()
        assert len(stars) == 1

        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.delete(f"/stars/{star_id}")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_message_stars(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, channel_message: Message
    ):
        data = {"type": "message", "reference": str(channel_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201

        assert (await authorized_client.get("/stars?type=channel")).json() == []
        assert (await authorized_client.get("/stars?type=server")).json() == []

        response = await authorized_client.get("/stars?type=message")
        assert response.status_code == 200

        stars = response.json()
        assert len(stars) == 1
        assert stars[0]["type"] == "message"
        assert stars[0]["reference"] == data["reference"]

    @pytest.mark.asyncio
    async def test_get_channel_stars(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server_channel: Channel
    ):
        data = {"type": "channel", "reference": str(server_channel.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201

        assert (await authorized_client.get("/stars?type=message")).json() == []

        response = await authorized_client.get("/stars?type=channel")
        assert response.status_code == 200

        stars = response.json()
        assert len(stars) == 1
        assert stars[0]["type"] == "channel"
        assert stars[0]["reference"] == data["reference"]

    @pytest.mark.asyncio
    async def test_create_star_user(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        create_new_user: Callable,
    ):
        fake_user = await create_new_user()
        data = {"type": "user", "reference": str(fake_user.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response["type"] == "user"
        assert json_response["reference"] == str(fake_user.id)

    @pytest.mark.asyncio
    async def test_get_user_stars(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        create_new_user: Callable,
    ):
        fake_user = await create_new_user()
        data = {"type": "user", "reference": str(fake_user.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201

        assert (await authorized_client.get("/stars?type=channel")).json() == []
        assert (await authorized_client.get("/stars?type=message")).json() == []

        response = await authorized_client.get("/stars?type=user")
        assert response.status_code == 200

        stars = response.json()
        assert len(stars) == 1
        assert stars[0]["type"] == "user"
        assert stars[0]["reference"] == data["reference"]

    @pytest.mark.asyncio
    async def test_create_star_wallet_address(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        create_new_user: Callable,
        wallet,
    ):
        data = {"type": "wallet_address", "reference": wallet}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response["type"] == "wallet_address"
        assert json_response["reference"] == wallet

    @pytest.mark.asyncio
    async def test_get_wallet_stars(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        create_new_user: Callable,
        wallet,
    ):
        data = {"type": "wallet_address", "reference": wallet}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201

        assert (await authorized_client.get("/stars?type=channel")).json() == []
        assert (await authorized_client.get("/stars?type=message")).json() == []
        assert (await authorized_client.get("/stars?type=user")).json() == []

        response = await authorized_client.get("/stars?type=wallet_address")
        assert response.status_code == 200

        stars = response.json()
        assert len(stars) == 1
        assert stars[0]["type"] == "wallet_address"
        assert stars[0]["reference"] == wallet
