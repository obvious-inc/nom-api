from datetime import datetime, timezone
from typing import Callable

import pytest
from bson import ObjectId
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.server import Server, ServerJoinRule, ServerMember
from app.models.user import User
from app.schemas.servers import ServerCreateSchema
from app.schemas.users import UserCreateSchema
from app.services.crud import get_item, get_items, update_item
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
        assert members[0].joined_at < datetime.now(timezone.utc)

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

    @pytest.mark.asyncio
    async def test_list_servers_empty(self, app: FastAPI, db: Database, authorized_client: AsyncClient):
        response = await authorized_client.get("/servers")
        assert response.status_code == 200
        assert len(response.json()) == 0

    @pytest.mark.asyncio
    async def test_list_public_servers_empty(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server
    ):
        response = await authorized_client.get("/servers")
        assert response.status_code == 200
        assert len(response.json()) == 0

    @pytest.mark.skip("public field not present yet")
    @pytest.mark.asyncio
    async def test_list_public_servers_not_empty(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server
    ):
        assert server.public is True
        response = await authorized_client.get("/servers")
        assert response.status_code == 200
        resp_servers = response.json()
        assert len(resp_servers) == 1
        resp_server = resp_servers[0]
        assert resp_server["id"] == str(server.id)

    @pytest.mark.asyncio
    async def test_join_server_no_rules(
        self,
        app: FastAPI,
        db: Database,
        server: Server,
        guest_user: User,
        get_authorized_client: Callable,
    ):
        guest_client = await get_authorized_client(guest_user)
        server_id = str(server.id)
        response = await guest_client.post(f"/servers/{server_id}/join")
        assert response.status_code == 201

        member = await get_item(
            filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember, current_user=guest_user
        )

        assert member is not None
        assert member.user == guest_user

    @pytest.mark.asyncio
    async def test_join_server_allowlist_rules_nok(
        self, app: FastAPI, db: Database, server: Server, guest_user: User, get_authorized_client: Callable
    ):
        rule = ServerJoinRule(type="allowlist", allowlist_addresses=[])
        await rule.commit()
        updated_server = await update_item(server, data={"join_rules": [rule]}, current_user=guest_user)
        assert len(updated_server.join_rules) == 1

        server_id = str(server.id)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{server_id}/join")
        assert response.status_code == 403

        member = await get_item(
            filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember, current_user=guest_user
        )
        assert member is None

    @pytest.mark.asyncio
    async def test_join_server_allowlist_rules_ok(
        self,
        app: FastAPI,
        db: Database,
        server: Server,
        guest_user: User,
        get_authorized_client: Callable,
    ):
        rule = ServerJoinRule(type="allowlist", allowlist_addresses=[guest_user.wallet_address])
        await rule.commit()
        updated_server = await update_item(server, data={"join_rules": [rule]}, current_user=guest_user)
        assert len(updated_server.join_rules) == 1

        server_id = str(server.id)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{server_id}/join")
        assert response.status_code == 201

        member = await get_item(
            filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember, current_user=guest_user
        )

        assert member is not None
        assert member.user == guest_user

    @pytest.mark.asyncio
    async def test_join_server_guild_rules_ok(
        self, app: FastAPI, db: Database, server: Server, guest_user: User, get_authorized_client: Callable
    ):
        rule = ServerJoinRule(type="guild_xyz", guild_xyz_id="1985")  # everyone has access to this guild
        await rule.commit()
        updated_server = await update_item(server, data={"join_rules": [rule]}, current_user=guest_user)
        assert len(updated_server.join_rules) == 1

        server_id = str(server.id)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{server_id}/join")
        assert response.status_code == 201

        member = await get_item(
            filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember, current_user=guest_user
        )
        assert member is not None
        assert member.user == guest_user

    @pytest.mark.asyncio
    async def test_join_server_guild_rules_nok(
        self, app: FastAPI, db: Database, server: Server, guest_user: User, get_authorized_client: Callable
    ):
        rule = ServerJoinRule(type="guild_xyz", guild_xyz_id="1898")
        await rule.commit()
        updated_server = await update_item(server, data={"join_rules": [rule]}, current_user=guest_user)
        assert len(updated_server.join_rules) == 1

        server_id = str(server.id)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{server_id}/join")
        assert response.status_code == 403

        member = await get_item(
            filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember, current_user=guest_user
        )
        assert member is None

    @pytest.mark.asyncio
    async def test_join_server_allowlist_ok_and_guild_nok(
        self,
        app: FastAPI,
        db: Database,
        server: Server,
        guest_user: User,
        get_authorized_client: Callable,
    ):
        guild_rule = ServerJoinRule(type="guild_xyz", guild_xyz_id="1898")
        await guild_rule.commit()
        allowlist_rule = ServerJoinRule(type="allowlist", allowlist_addresses=[guest_user.wallet_address])
        await allowlist_rule.commit()
        updated_server = await update_item(
            server, data={"join_rules": [allowlist_rule, guild_rule]}, current_user=guest_user
        )
        assert len(updated_server.join_rules) == 2

        server_id = str(server.id)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{server_id}/join")
        assert response.status_code == 201

        member = await get_item(
            filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember, current_user=guest_user
        )

        assert member is not None
        assert member.user == guest_user

    @pytest.mark.asyncio
    async def test_join_server_allowlist_nok_and_guild_ok(
        self,
        app: FastAPI,
        db: Database,
        server: Server,
        guest_user: User,
        get_authorized_client: Callable,
    ):
        guild_rule = ServerJoinRule(type="guild_xyz", guild_xyz_id="1985")
        await guild_rule.commit()
        allowlist_rule = ServerJoinRule(type="allowlist", allowlist_addresses=[])
        await allowlist_rule.commit()
        updated_server = await update_item(
            server, data={"join_rules": [allowlist_rule, guild_rule]}, current_user=guest_user
        )
        assert len(updated_server.join_rules) == 2

        server_id = str(server.id)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{server_id}/join")
        assert response.status_code == 201

        member = await get_item(
            filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember, current_user=guest_user
        )

        assert member is not None
        assert member.user == guest_user
