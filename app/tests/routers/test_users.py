from typing import Callable

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.channel import Channel
from app.models.server import Server
from app.models.user import User


class TestUserRoutes:
    @pytest.mark.asyncio
    async def test_get_user_me(self, app: FastAPI, db: Database, authorized_client: AsyncClient):
        response = await authorized_client.get("/users/me")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_servers_unauthorized(self, app: FastAPI, db: Database, client: AsyncClient):
        response = await client.get("/users/me/servers")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_servers_empty(self, app: FastAPI, db: Database, authorized_client: AsyncClient):
        response = await authorized_client.get("/users/me/servers")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_servers_ok(self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server):
        response = await authorized_client.get("/users/me/servers")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response != []
        assert len(json_response) == 1
        json_server = json_response[0]
        assert json_server["id"] == str(server.id)
        assert json_server["name"] == server.name

    @pytest.mark.asyncio
    async def test_get_user_profile(self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server):
        response = await authorized_client.get(f"/users/me?server_id={str(server.id)}")
        assert response.status_code == 200
        json_response = response.json()
        assert "display_name" in json_response

    @pytest.mark.asyncio
    async def test_update_user_profile_display_name(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server
    ):
        response = await authorized_client.get(f"/users/me?server_id={str(server.id)}")
        assert response.status_code == 200
        json_response = response.json()
        assert "display_name" in json_response
        old_display_name = json_response["display_name"]

        data = {"display_name": "new_name.eth"}
        response = await authorized_client.patch(f"/users/me?server_id={str(server.id)}", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert "display_name" in json_response
        assert json_response["display_name"] != old_display_name
        assert json_response["display_name"] == data["display_name"]

    @pytest.mark.asyncio
    async def test_update_user_profile_description(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server
    ):
        response = await authorized_client.get("/users/me")
        assert response.status_code == 200
        json_response = response.json()
        assert "description" in json_response
        assert json_response["description"] == ""

        data = {"description": "New description!"}
        response = await authorized_client.patch("/users/me", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert "description" in json_response
        assert json_response["description"] == data["description"]

    @pytest.mark.asyncio
    async def test_update_user_ens_domain(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server
    ):
        response = await authorized_client.get("/users/me")
        assert response.status_code == 200
        json_response = response.json()
        assert "ens_domain" in json_response
        assert json_response["ens_domain"] is None

        data = {"ens_domain": "vitalik.eth"}
        response = await authorized_client.patch("/users/me", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert "ens_domain" in json_response
        assert json_response["ens_domain"] == data["ens_domain"]

    @pytest.mark.asyncio
    async def test_update_user_profile_display_name_empty(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server
    ):
        response = await authorized_client.get(f"/users/me?server_id={str(server.id)}")
        assert response.status_code == 200
        json_response = response.json()
        assert "display_name" in json_response
        old_display_name = json_response["display_name"]

        data = {"display_name": ""}
        response = await authorized_client.patch(f"/users/me?server_id={str(server.id)}", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert "display_name" in json_response
        assert json_response["display_name"] != old_display_name
        assert json_response["display_name"] == data["display_name"]

    @pytest.mark.asyncio
    async def test_list_channels_ok(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, topic_channel: Channel, dm_channel: Channel
    ):
        response = await authorized_client.get("/users/me/channels")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response != []
        assert len(json_response) == 2

    @pytest.mark.asyncio
    async def test_update_user_push_tokens(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server, current_user: User
    ):
        assert len(current_user.push_tokens) == 0

        push_token_id = "token1"
        data = {"push_tokens": [push_token_id]}
        response = await authorized_client.patch("/users/me", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert "push_tokens" not in json_response

        await current_user.reload()
        assert len(current_user.push_tokens) == 1
        assert current_user.push_tokens == data["push_tokens"]

    @pytest.mark.asyncio
    async def test_get_empty_user_preferences(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        response = await authorized_client.get("/users/me/preferences")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_patch_user_preferences_create(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        topic_channel: Channel,
    ):
        data = {"channels": {str(topic_channel.pk): {"muted": True}}}
        response = await authorized_client.put("/users/me/preferences", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response != {}

        response = await authorized_client.get("/users/me/preferences")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response != {}
        assert "channels" in json_response
        channel_prefs = json_response.get("channels")
        topic_channel_prefs = channel_prefs.get(str(topic_channel.pk))
        assert topic_channel_prefs is not None
        assert topic_channel_prefs != {}

    @pytest.mark.asyncio
    async def test_patch_user_preferences_update(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        topic_channel: Channel,
    ):
        data = {"channels": {str(topic_channel.pk): {"muted": True}}}
        response = await authorized_client.put("/users/me/preferences", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert "channels" in json_response
        channel_prefs = json_response.get("channels")
        topic_channel_prefs = channel_prefs.get(str(topic_channel.pk))
        assert topic_channel_prefs is not None
        assert topic_channel_prefs != {}
        assert topic_channel_prefs.get("muted") is True

        data = {"channels": {str(topic_channel.pk): {"muted": False}}}
        response = await authorized_client.put("/users/me/preferences", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert "channels" in json_response
        channel_prefs = json_response.get("channels")
        topic_channel_prefs = channel_prefs.get(str(topic_channel.pk))
        assert topic_channel_prefs is not None
        assert topic_channel_prefs != {}
        assert topic_channel_prefs.get("muted") is False

    @pytest.mark.asyncio
    async def test_post_report_user(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, current_user: User, create_new_user: Callable
    ):
        guest_user = await create_new_user()

        response = await authorized_client.post("/users/me/reports", json={"user": str(guest_user.pk)})
        assert response.status_code == 201
        json_resp = response.json()
        assert json_resp.get("author") == str(current_user.pk)
        assert json_resp.get("user") == str(guest_user.pk)
        assert json_resp.get("reason") == "other"

    @pytest.mark.asyncio
    async def test_post_report_user_self(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
    ):
        response = await authorized_client.post("/users/me/reports", json={"user": str(current_user.pk)})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_post_report_user_already_reported(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, current_user: User, create_new_user: Callable
    ):
        guest_user = await create_new_user()

        response = await authorized_client.post("/users/me/reports", json={"user": str(guest_user.pk)})
        assert response.status_code == 201

        response = await authorized_client.post("/users/me/reports", json={"user": str(guest_user.pk)})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_post_block_user(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, current_user: User, create_new_user: Callable
    ):
        guest_user = await create_new_user()

        response = await authorized_client.post("/users/me/blocks", json={"user": str(guest_user.pk)})
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_post_block_user_self(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
    ):
        response = await authorized_client.post("/users/me/blocks", json={"user": str(current_user.pk)})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_post_block_user_already_blocked(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, current_user: User, create_new_user: Callable
    ):
        guest_user = await create_new_user()

        response = await authorized_client.post("/users/me/blocks", json={"user": str(guest_user.pk)})
        assert response.status_code == 204

        response = await authorized_client.post("/users/me/blocks", json={"user": str(guest_user.pk)})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_list_blocked_users(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, current_user: User, create_new_user: Callable
    ):
        guest_user = await create_new_user()

        response = await authorized_client.post("/users/me/blocks", json={"user": str(guest_user.pk)})
        assert response.status_code == 204

        response = await authorized_client.get("/users/me/blocks")
        assert response.status_code == 200
        json_resp = response.json()
        assert len(json_resp) == 1
        print(json_resp)
        assert json_resp[0].get("user") == str(guest_user.pk)
        assert json_resp[0].get("author") == str(current_user.pk)

    @pytest.mark.asyncio
    async def test_unblock_user(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, current_user: User, create_new_user: Callable
    ):
        guest_user = await create_new_user()

        response = await authorized_client.post("/users/me/blocks", json={"user": str(guest_user.pk)})
        assert response.status_code == 204

        response = await authorized_client.get("/users/me/blocks")
        assert response.status_code == 200
        json_resp = response.json()
        assert len(json_resp) == 1

        response = await authorized_client.delete(f"/users/me/blocks/{str(guest_user.pk)}")
        assert response.status_code == 204

        response = await authorized_client.get("/users/me/blocks")
        assert response.status_code == 200
        json_resp = response.json()
        assert len(json_resp) == 0

    @pytest.mark.asyncio
    async def test_unblock_user_not_blocked(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, current_user: User, create_new_user: Callable
    ):
        guest_user = await create_new_user()

        response = await authorized_client.delete(f"/users/me/blocks/{str(guest_user.pk)}")
        assert response.status_code == 404
