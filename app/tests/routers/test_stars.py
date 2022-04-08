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
        data = {"message": str(channel_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response["type"] == "message"
        assert json_response["message"] == str(channel_message.id)

    @pytest.mark.asyncio
    async def test_create_star_dm(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, direct_message: Message
    ):
        data = {"message": str(direct_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response["type"] == "message"
        assert json_response["message"] == str(direct_message.id)

    @pytest.mark.asyncio
    async def test_create_star_server_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server_channel: Channel
    ):
        data = {"channel": str(server_channel.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response["type"] == "channel"
        assert json_response["channel"] == str(server_channel.id)

    @pytest.mark.asyncio
    async def test_create_star_dm_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, dm_channel: Channel
    ):
        data = {"channel": str(dm_channel.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response["type"] == "channel"
        assert json_response["channel"] == str(dm_channel.id)

    @pytest.mark.asyncio
    async def test_create_star_server(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        data = {"server": str(server.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response["type"] == "server"
        assert json_response["server"] == str(server.id)

    @pytest.mark.asyncio
    async def test_create_star_random(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        data = {"random": "whatevz"}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_star_multiple_times(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, channel_message: Message
    ):
        data = {"message": str(channel_message.id)}
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
        data = {"message": str(channel_message.id)}
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

        data = {"message": str(channel_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201

        stars = (await authorized_client.get("/stars")).json()

        assert len(stars) == 1
        assert stars[0]["type"] == "message"
        assert stars[0]["message"] == str(channel_message.id)

    @pytest.mark.asyncio
    async def test_delete_star(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, channel_message: Message
    ):
        data = {"message": str(channel_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201

        star_id = response.json()["id"]

        response = await authorized_client.delete(f"/stars/{star_id}")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_star_multiple_times(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, channel_message: Message
    ):
        data = {"message": str(channel_message.id)}
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
        data = {"message": str(channel_message.id)}
        response = await authorized_client.post("/stars", json=data)
        assert response.status_code == 201
        star_id = response.json()["id"]

        stars = (await authorized_client.get("/stars")).json()
        assert len(stars) == 1

        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.delete(f"/stars/{star_id}")
        assert response.status_code == 403
