from typing import Callable

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.channel import Channel
from app.models.server import Server
from app.models.user import User
from app.schemas.servers import ServerCreateSchema
from app.services.servers import create_server


class TestChannelsRoutes:
    @pytest.mark.asyncio
    async def test_create_dm_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        members = []
        for x in range(3):
            user = User(wallet_address=f"0x{x}")
            await user.commit()
            members.append(user)

        data = {"kind": "dm", "members": [str(member.id) for member in members]}

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == data["kind"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert "members" in json_response
        assert all([member in json_response["members"] for member in data["members"]])
        assert str(current_user.id) in json_response["members"]

    @pytest.mark.asyncio
    async def test_create_personal_dm_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        data = {"kind": "dm", "members": []}

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == data["kind"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert "members" in json_response
        assert str(current_user.id) in json_response["members"]

    @pytest.mark.asyncio
    async def test_create_multiple_personal_dm_channels(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        data = {"kind": "dm", "members": []}

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == data["kind"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert "members" in json_response
        assert str(current_user.id) in json_response["members"]
        channel_id = json_response["id"]

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response["id"] == channel_id

    @pytest.mark.asyncio
    async def test_create_server_channel(
        self, app: FastAPI, db: Database, current_user: User, server: Server, authorized_client: AsyncClient
    ):
        data = {
            "kind": "server",
            "name": "fancy-announcements",
            "server": str(server.id),
        }

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == data["kind"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert "name" in json_response
        assert json_response["name"] == data["name"]
        assert "server" in json_response
        assert json_response["server"] == str(server.id)

    @pytest.mark.asyncio
    async def test_create_server_channel_not_owner(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        server: Server,
        authorized_client: AsyncClient,
        create_new_user: Callable,
        get_authorized_client: Callable,
    ):
        data = {
            "kind": "server",
            "name": "fancy-announcements",
            "server": str(server.id),
        }
        member = await create_new_user()
        member_auth_client = await get_authorized_client(member)

        response = await member_auth_client.post("/channels", json=data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_server_channel_with_emojis(
        self, app: FastAPI, db: Database, current_user: User, server: Server, authorized_client: AsyncClient
    ):
        data = {
            "kind": "server",
            "name": "📣-fancy-announcements",
            "server": str(server.id),
        }

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == data["kind"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert "name" in json_response
        assert json_response["name"] == data["name"]
        assert "server" in json_response
        assert json_response["server"] == str(server.id)

    @pytest.mark.asyncio
    async def test_delete_channel_ok(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server, server_channel: Channel
    ):
        response = await authorized_client.delete(f"/channels/{str(server_channel.id)}")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["id"] == str(server_channel.id)
        assert json_response["name"] == server_channel.name
        assert json_response["server"] == str(server.id)
        assert json_response["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_dm_channel(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server, dm_channel: Channel
    ):
        response = await authorized_client.delete(f"/channels/{str(dm_channel.id)}")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_channel_no_permission(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        guest_user: User,
    ):
        server = await create_server(ServerCreateSchema(name="test Server"), current_user=guest_user)
        new_channel = Channel(server=server.id, owner=guest_user.id, kind="server")
        await new_channel.commit()

        response = await authorized_client.delete(f"/channels/{str(new_channel.id)}")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_server_channel_ok(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        server_channel: Channel,
    ):
        data = {"name": "my-channel!"}
        response = await authorized_client.patch(f"/channels/{str(server_channel.pk)}", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["name"] == data["name"]

    @pytest.mark.asyncio
    async def test_update_dm_channel_ok(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        dm_channel: Channel,
    ):
        data = {"name": "kool & the gang"}
        response = await authorized_client.patch(f"/channels/{str(dm_channel.pk)}", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["name"] == data["name"]

    @pytest.mark.asyncio
    async def test_update_server_channel_as_guest_fails(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        server_channel: Channel,
        create_new_user: Callable,
        get_authorized_client: Callable,
    ):
        member = await create_new_user()
        member_auth_client = await get_authorized_client(member)

        data = {"name": "my-channel!"}
        response = await member_auth_client.patch(f"/channels/{str(server_channel.pk)}", json=data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_dm_channel_as_non_member_fails(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        dm_channel: Channel,
        create_new_user: Callable,
        get_authorized_client: Callable,
    ):
        member = await create_new_user()
        member_auth_client = await get_authorized_client(member)

        data = {"name": "my-channel!"}
        response = await member_auth_client.patch(f"/channels/{str(dm_channel.pk)}", json=data)
        assert response.status_code == 403

    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_update_dm_channel_remove_member_as_not_owner(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        create_new_user: Callable,
        get_authorized_client: Callable,
    ):
        guest = await create_new_user()
        guest_client = await get_authorized_client(guest)

        members = [current_user, guest]
        data = {"kind": "dm", "members": [str(member.id) for member in members]}

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        channel_id = response.json().get("id")

        data = {"members": [str(guest.id)]}
        response = await guest_client.patch(f"/channels/{channel_id}", json=data)
        assert response.status_code == 403
