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
