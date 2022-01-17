import pytest
from bson import ObjectId
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.user import User


class TestServerRoutes:
    @pytest.mark.asyncio
    async def test_list_servers_unauthorized(self, app: FastAPI, db: Database, client: AsyncClient):
        response = await client.get("/servers")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_servers_empty(self, app: FastAPI, db: Database, authorized_client: AsyncClient):
        response = await authorized_client.get("/servers")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_create_server(self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient):
        server_name = "test"
        response = await authorized_client.post("/servers", json={"name": server_name})
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "name" in json_response
        assert "id" in json_response
        assert json_response["id"] is not None
        assert json_response["name"] == server_name
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)

    @pytest.mark.asyncio
    async def test_create_server_right_objectid_type(self, app: FastAPI, db: Database, authorized_client: AsyncClient):
        server_name = "test"
        response = await authorized_client.post("/servers", json={"name": server_name})
        assert response.status_code == 201
        obj = await db["servers"].find_one()
        assert type(obj["_id"]) != str
        assert type(obj["_id"]) == ObjectId
