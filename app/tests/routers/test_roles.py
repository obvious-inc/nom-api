import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.constants.permissions import Permission
from app.helpers.cache_utils import cache
from app.models.server import Server
from app.models.user import User


class TestRoleRoutes:
    @pytest.mark.asyncio
    async def test_create_role(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        response = await authorized_client.get(f"/servers/{str(server.pk)}/roles")
        assert response.status_code == 200
        json_resp = response.json()
        assert len(json_resp) == 1
        assert json_resp[0]["name"] == "@everyone"

        new_role = {"name": "mod", "permissions": [Permission.MEMBERS_KICK.value]}

        response = await authorized_client.post(f"/servers/{str(server.pk)}/roles", json=new_role)
        assert response.status_code == 201

        response = await authorized_client.get(f"/servers/{str(server.pk)}/roles")
        assert response.status_code == 200
        json_resp = response.json()
        assert len(json_resp) == 2
        assert json_resp[0]["name"] == new_role["name"]
        resp_roles = {role["id"]: ",".join(role["permissions"]) for role in json_resp}

        for role, perms in resp_roles.items():
            cached_perms = await cache.client.hget(f"server:{str(server.pk)}", f"roles.{role}")
            assert cached_perms == perms

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "role_name, success",
        [("@role", False), ("mod", True)],
    )
    async def test_create_role_names(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        role_name: str,
        success: bool,
    ):
        new_role = {"name": role_name, "permissions": [Permission.MESSAGES_LIST.value]}
        if success:
            response = await authorized_client.post(f"/servers/{str(server.pk)}/roles", json=new_role)
            assert response.status_code == 201
        else:
            with pytest.raises(Exception):
                await authorized_client.post(f"/servers/{str(server.pk)}/roles", json=new_role)
