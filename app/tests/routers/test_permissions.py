from typing import Callable, List

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.channel import Channel
from app.models.server import Server, ServerMember
from app.models.user import Role, User
from app.schemas.users import RoleCreateSchema
from app.services.crud import create_item, get_item, update_item


class TestPermissionsRoutes:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "permissions, status",
        [
            (["messages.list"], 200),
            (["messages.create", "members.kick"], 403),
            ([], 403),
            (["messages.list", "members.kick", "members.ban"], 200),
        ],
    )
    async def test_fetch_messages_as_guest(
        self,
        app: FastAPI,
        db: Database,
        guest_user: User,
        get_authorized_client: Callable,
        server: Server,
        server_channel: Channel,
        permissions: List[str],
        status: int,
    ):
        role_schema = RoleCreateSchema(name="test", server=str(server.pk), permissions=permissions)
        role = await create_item(item=role_schema, result_obj=Role, current_user=guest_user, user_field=None)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{str(server.pk)}/join")
        assert response.status_code == 201

        member = await get_item(
            filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember, current_user=guest_user
        )
        assert member is not None
        await update_item(item=member, data={"roles": [role]}, current_user=guest_user)

        response = await guest_client.get(f"/channels/{str(server_channel.id)}/messages")
        assert response.status_code == status

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "permissions, status",
        [
            (["messages.list"], 200),
            (["messages.create", "members.kick"], 200),
            ([], 200),
            (["messages.list", "members.kick", "members.ban"], 200),
        ],
    )
    async def test_fetch_messages_as_server_owner(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        permissions: List[str],
        status: int,
    ):
        role_schema = RoleCreateSchema(name="test", server=str(server.pk), permissions=permissions)
        role = await create_item(item=role_schema, result_obj=Role, current_user=current_user, user_field=None)

        member = await get_item(
            filters={"server": server.pk, "user": current_user.pk}, result_obj=ServerMember, current_user=current_user
        )
        assert member is not None
        await update_item(item=member, data={"roles": [role]}, current_user=current_user)

        response = await authorized_client.get(f"/channels/{str(server_channel.id)}/messages")
        assert response.status_code == status

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "permissions, status",
        [
            ([], 403),
            (["messages.list"], 403),
            (["messages.create", "members.kick"], 403),
            (["messages.list", "members.kick", "members.ban"], 403),
            (["messages.list", "messages.create", "channels.create"], 201),
        ],
    )
    async def test_create_channel_as_guest(
        self,
        app: FastAPI,
        db: Database,
        guest_user: User,
        get_authorized_client: Callable,
        server: Server,
        server_channel: Channel,
        permissions: List[str],
        status: int,
    ):
        role_schema = RoleCreateSchema(name="test", server=str(server.pk), permissions=permissions)
        role = await create_item(item=role_schema, result_obj=Role, current_user=guest_user, user_field=None)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{str(server.pk)}/join")
        assert response.status_code == 201

        member = await get_item(
            filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember, current_user=guest_user
        )
        assert member is not None
        await update_item(item=member, data={"roles": [role]}, current_user=guest_user)

        data = {"kind": "server", "name": "fancy-announcements", "server": str(server.id)}
        response = await guest_client.post("/channels", json=data)
        assert response.status_code == status
