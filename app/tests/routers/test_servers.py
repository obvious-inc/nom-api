from datetime import datetime

import pytest
from bson import ObjectId
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.server import Server, ServerMember
from app.models.user import User
from app.schemas.servers import ServerCreateSchema
from app.schemas.users import UserCreateSchema
from app.services.crud import get_item, get_items
from app.services.servers import create_server
from app.services.users import create_user


class TestServerRoutes:
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
        obj = await get_item(filters={}, result_obj=Server)
        assert type(obj["id"]) != str
        assert type(obj["id"]) == ObjectId

    @pytest.mark.asyncio
    async def test_create_server_add_member(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
    ):
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

        members = await get_items(
            {"server": ObjectId(json_response["id"])}, result_obj=ServerMember, current_user=current_user, size=None
        )
        assert len(members) == 1
        assert members[0].user == current_user
        assert members[0].joined_at < datetime.utcnow()

    @pytest.mark.asyncio
    async def test_list_server_members(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
    ):
        response = await authorized_client.get(f"/servers/{str(server.id)}/members")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 1
        server_member = json_response[0]
        assert server_member["server"] == str(server.id)
        assert server_member["user"] == str(current_user.id)

    @pytest.mark.asyncio
    async def test_list_server_members_non_member_fail(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
    ):
        server_model = ServerCreateSchema(name="Private DAO")
        new_user = await create_user(UserCreateSchema(wallet_address="0x0000000000000000000000000000000000000000"))
        new_server = await create_server(server_model, current_user=new_user)

        response = await authorized_client.get(f"/servers/{str(new_server.id)}/members")
        assert response.status_code == 403
