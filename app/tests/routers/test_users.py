import json
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.server import Server


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
        assert "description" in json_response

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
        response = await authorized_client.get(f"/users/me?server_id={str(server.id)}")
        assert response.status_code == 200
        json_response = response.json()
        print(json_response)
        assert "description" in json_response
        old_description = json_response["description"]

        data = {"description": "I love low gas prices!"}
        response = await authorized_client.patch(f"/users/me?server_id={str(server.id)}", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert "description" in json_response
        assert json_response["description"] != old_description
        assert json_response["description"] == data["description"]

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
