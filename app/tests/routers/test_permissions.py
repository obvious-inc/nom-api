from typing import Callable, Dict, List

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.channel import Channel
from app.models.section import Section
from app.models.server import Server, ServerMember
from app.models.user import Role, User
from app.schemas.channels import ServerChannelCreateSchema
from app.schemas.sections import SectionCreateSchema
from app.schemas.servers import ServerCreateSchema
from app.schemas.users import RoleCreateSchema
from app.services.channels import create_server_channel
from app.services.crud import create_item, get_item, update_item
from app.services.roles import create_role
from app.services.servers import create_server


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
        role = await create_role(
            server_id=str(server.pk),
            role_model=role_schema,
            current_user=guest_user,
            internal=True,
        )
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{str(server.pk)}/join")
        assert response.status_code == 201

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)
        assert member is not None
        await update_item(item=member, data={"roles": [role]})

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
        role = await create_role(
            server_id=str(server.pk),
            role_model=role_schema,
            current_user=current_user,
            internal=True,
        )

        member = await get_item(filters={"server": server.pk, "user": current_user.pk}, result_obj=ServerMember)
        assert member is not None
        await update_item(item=member, data={"roles": [role]})

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
        role = await create_role(
            server_id=str(server.pk),
            role_model=role_schema,
            current_user=guest_user,
            internal=True,
        )
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{str(server.pk)}/join")
        assert response.status_code == 201

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)
        assert member is not None
        await update_item(item=member, data={"roles": [role]})

        data = {"kind": "server", "name": "fancy-announcements", "server": str(server.id)}
        response = await guest_client.post("/channels", json=data)
        assert response.status_code == status

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "role_permissions, channel_overwrites, status",
        [
            (["messages.list"], None, 200),
            (["messages.list"], [], 403),
            (["messages.list"], ["messages.create"], 403),
            (["messages.list"], ["messages.create", "messages.list"], 200),
            (["messages.create"], ["messages.create"], 403),
            (["messages.create"], None, 403),
            (["channels.view"], ["messages.list"], 200),
        ],
    )
    async def test_fetch_messages_as_guest_with_channel_overwrites(
        self,
        app: FastAPI,
        db: Database,
        guest_user: User,
        get_authorized_client: Callable,
        server: Server,
        server_channel: Channel,
        role_permissions: List[str],
        status: int,
        channel_overwrites: List[str],
    ):
        default_role = "@everyone"
        role_schema = RoleCreateSchema(name=default_role, server=str(server.pk), permissions=role_permissions)
        role = await create_role(
            server_id=str(server.pk),
            role_model=role_schema,
            current_user=guest_user,
            internal=True,
        )
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{str(server.pk)}/join")
        assert response.status_code == 201

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)
        assert member is not None
        await update_item(item=member, data={"roles": [role]})

        if channel_overwrites is not None:
            data = {"permission_overwrites": [{"role": role.pk, "permissions": channel_overwrites}]}
            await update_item(item=server_channel, data=data)

        response = await guest_client.get(f"/channels/{str(server_channel.id)}/messages")
        assert response.status_code == status

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "role_permissions, section_overwrites, status",
        [
            (["messages.list"], None, 200),
            (["messages.list"], [], 403),
            (["messages.list"], ["messages.create"], 403),
            (["messages.list"], ["messages.create", "messages.list"], 200),
            (["messages.create"], ["messages.create"], 403),
            (["messages.create"], None, 403),
            (["channels.view"], ["messages.list"], 200),
        ],
    )
    async def test_fetch_messages_as_guest_with_section_overwrites(
        self,
        app: FastAPI,
        db: Database,
        guest_user: User,
        get_authorized_client: Callable,
        server: Server,
        server_channel: Channel,
        role_permissions: List[str],
        status: int,
        section_overwrites: List[str],
    ):
        default_role = "@everyone"
        role_schema = RoleCreateSchema(name=default_role, server=str(server.pk), permissions=role_permissions)
        role = await create_role(
            server_id=str(server.pk),
            role_model=role_schema,
            current_user=guest_user,
            internal=True,
        )
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{str(server.pk)}/join")
        assert response.status_code == 201

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)
        assert member is not None
        await update_item(item=member, data={"roles": [role]})

        if section_overwrites is not None:
            section_model = SectionCreateSchema(name="who-cares", server=str(server.pk))
            section = await create_item(section_model, result_obj=Section, current_user=guest_user, user_field=None)
            data = {
                "channels": [str(server_channel.pk)],
                "permission_overwrites": [{"role": role.pk, "permissions": section_overwrites}],
            }
            await update_item(item=section, data=data)

        response = await guest_client.get(f"/channels/{str(server_channel.id)}/messages")
        assert response.status_code == status

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "role_permissions, section_overwrites, channel_overwrites, status",
        [
            (["messages.list"], None, None, 200),
            (["messages.list"], [], None, 403),
            (["messages.list"], None, [], 403),
            ([], ["messages.list"], None, 200),
            ([], None, ["messages.list"], 200),
            (["messages.list"], [], ["messages.list"], 200),
            ([], ["messages.list"], None, 200),
            ([], None, ["messages.list"], 200),
            ([], ["messages.list"], [], 403),
        ],
    )
    async def test_fetch_messages_as_guest_with_channel_and_section_overwrites(
        self,
        app: FastAPI,
        db: Database,
        guest_user: User,
        get_authorized_client: Callable,
        server: Server,
        server_channel: Channel,
        role_permissions: List[str],
        status: int,
        section_overwrites: List[str],
        channel_overwrites: List[str],
    ):
        default_role = "@everyone"
        role_schema = RoleCreateSchema(name=default_role, server=str(server.pk), permissions=role_permissions)
        role = await create_role(
            server_id=str(server.pk),
            role_model=role_schema,
            current_user=guest_user,
            internal=True,
        )
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{str(server.pk)}/join")
        assert response.status_code == 201

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)
        assert member is not None
        await update_item(item=member, data={"roles": [role]})

        if section_overwrites is not None:
            section_model = SectionCreateSchema(name="who-cares", server=str(server.pk))
            section = await create_item(section_model, result_obj=Section, current_user=guest_user, user_field=None)
            data = {
                "channels": [str(server_channel.pk)],
                "permission_overwrites": [{"role": role.pk, "permissions": section_overwrites}],
            }
            await update_item(item=section, data=data)

        if channel_overwrites is not None:
            data = {"permission_overwrites": [{"role": role.pk, "permissions": channel_overwrites}]}
            await update_item(item=server_channel, data=data)

        response = await guest_client.get(f"/channels/{str(server_channel.id)}/messages")
        assert response.status_code == status

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "role_permissions, section_overwrites, channel_overwrites, status",
        [
            ({"guest": ["messages.list"]}, None, None, 200),
            ({"guest": []}, None, None, 403),
            ({"guest": [], "mod": ["messages.list"]}, None, None, 200),
            ({"guest": []}, {"guest": ["messages.list"]}, None, 200),
            ({"guest": [], "mod": ["messages.list"]}, {"mod": []}, None, 403),
            ({"guest": [], "mod": []}, {"mod": ["messages.list"]}, None, 200),
            ({"guest": [], "mod": []}, None, {"mod": ["messages.list"]}, 200),
            ({"guest": [], "mod": ["messages.list"]}, None, {"mod": []}, 403),
            ({"guest": [], "mod": []}, {"mod": ["messages.list"]}, {"mod": []}, 403),
            ({"guest": [], "mod": []}, {"guest": ["messages.list"], "mod": ["messages.list"]}, {"guest": []}, 200),
        ],
    )
    async def test_fetch_messages_as_guest_with_channel_and_section_overwrites_multiple_roles(
        self,
        app: FastAPI,
        db: Database,
        guest_user: User,
        get_authorized_client: Callable,
        server: Server,
        server_channel: Channel,
        role_permissions: Dict[str, List[str]],
        status: int,
        section_overwrites: Dict[str, List[str]],
        channel_overwrites: Dict[str, List[str]],
    ):
        roles = []
        for role_name, permissions in role_permissions.items():
            role_schema = RoleCreateSchema(name=role_name, server=str(server.pk), permissions=permissions)
            role = await create_role(
                server_id=str(server.pk),
                role_model=role_schema,
                current_user=guest_user,
                internal=True,
            )
            roles.append(role)

        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{str(server.pk)}/join")
        assert response.status_code == 201

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)
        assert member is not None
        await update_item(item=member, data={"roles": [role.pk for role in roles]})

        if section_overwrites is not None:
            section_model = SectionCreateSchema(name="who-cares", server=str(server.pk))
            section = await create_item(section_model, result_obj=Section, current_user=guest_user, user_field=None)

            ow = []
            for s_role_name, s_role_permissions in section_overwrites.items():
                role = await get_item(filters={"name": s_role_name, "server": server.pk}, result_obj=Role)
                ow.append({"role": role.pk, "permissions": s_role_permissions})
            data = {"channels": [str(server_channel.pk)], "permission_overwrites": ow}

            await update_item(item=section, data=data)

        if channel_overwrites is not None:
            ow = []
            for c_role_name, c_role_permissions in channel_overwrites.items():
                role = await get_item(filters={"name": c_role_name, "server": server.pk}, result_obj=Role)
                ow.append({"role": role.pk, "permissions": c_role_permissions})
            data = {"permission_overwrites": ow}
            await update_item(item=server_channel, data=data)

        response = await guest_client.get(f"/channels/{str(server_channel.id)}/messages")
        assert response.status_code == status

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "role_permissions, section_overwrites, channel_overwrites, status",
        [
            ({"guest": ["messages.list"]}, None, None, 200),
            ({"guest": []}, None, None, 403),
            ({"guest": [], "mod": ["messages.list"]}, None, None, 200),
            ({"guest": []}, {"guest": ["messages.list"]}, None, 200),
            ({"guest": [], "mod": ["messages.list"]}, {"mod": []}, None, 403),
            ({"guest": [], "mod": []}, {"mod": ["messages.list"]}, None, 200),
            ({"guest": [], "mod": []}, None, {"mod": ["messages.list"]}, 200),
            ({"guest": [], "mod": ["messages.list"]}, None, {"mod": []}, 403),
            ({"guest": [], "mod": []}, {"mod": ["messages.list"]}, {"mod": []}, 403),
            ({"guest": [], "mod": []}, {"guest": ["messages.list"], "mod": ["messages.list"]}, {"guest": []}, 200),
        ],
    )
    async def test_fetch_messages_as_guest_with_channel_and_section_overwrites_multiple_roles_cached(
        self,
        app: FastAPI,
        db: Database,
        guest_user: User,
        get_authorized_client: Callable,
        server: Server,
        server_channel: Channel,
        role_permissions: Dict[str, List[str]],
        status: int,
        section_overwrites: Dict[str, List[str]],
        channel_overwrites: Dict[str, List[str]],
    ):
        roles = []
        for role_name, permissions in role_permissions.items():
            role_schema = RoleCreateSchema(name=role_name, server=str(server.pk), permissions=permissions)
            role = await create_role(
                server_id=str(server.pk),
                role_model=role_schema,
                current_user=guest_user,
                internal=True,
            )
            roles.append(role)

        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{str(server.pk)}/join")
        assert response.status_code == 201

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)
        assert member is not None
        await update_item(item=member, data={"roles": [role.pk for role in roles]})

        if section_overwrites is not None:
            section_model = SectionCreateSchema(name="who-cares", server=str(server.pk))
            section = await create_item(section_model, result_obj=Section, current_user=guest_user, user_field=None)

            ow = []
            for s_role_name, s_role_permissions in section_overwrites.items():
                role = await get_item(filters={"name": s_role_name, "server": server.pk}, result_obj=Role)
                ow.append({"role": role.pk, "permissions": s_role_permissions})
            data = {"channels": [str(server_channel.pk)], "permission_overwrites": ow}

            await update_item(item=section, data=data)

        if channel_overwrites is not None:
            ow = []
            for c_role_name, c_role_permissions in channel_overwrites.items():
                role = await get_item(filters={"name": c_role_name, "server": server.pk}, result_obj=Role)
                ow.append({"role": role.pk, "permissions": c_role_permissions})
            data = {"permission_overwrites": ow}
            await update_item(item=server_channel, data=data)

        response = await guest_client.get(f"/channels/{str(server_channel.id)}/messages")
        assert response.status_code == status

        response = await guest_client.get(f"/channels/{str(server_channel.id)}/messages")
        assert response.status_code == status

    @pytest.mark.asyncio
    async def test_fetch_dm_messages_as_member(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        get_authorized_client: Callable,
        dm_channel: Channel,
    ):
        client = await get_authorized_client(current_user)
        response = await client.get(f"/channels/{str(dm_channel.id)}/messages")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_dm_messages_as_non_member(
        self,
        app: FastAPI,
        db: Database,
        guest_user: User,
        get_authorized_client: Callable,
        dm_channel: Channel,
    ):
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.get(f"/channels/{str(dm_channel.id)}/messages")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_multiple_servers(
        self, app: FastAPI, db: Database, current_user: User, guest_user: User, get_authorized_client: Callable
    ):
        server1 = await create_server(ServerCreateSchema(name="server1"), current_user=current_user)
        channel1_model = ServerChannelCreateSchema(kind="server", server=str(server1.id), name="channel1")
        channel1 = await create_server_channel(channel_model=channel1_model, current_user=current_user)

        server2 = await create_server(ServerCreateSchema(name="server2"), current_user=current_user)
        channel2_model = ServerChannelCreateSchema(kind="server", server=str(server2.id), name="channel2")
        channel2 = await create_server_channel(channel_model=channel2_model, current_user=current_user)

        guest_client = await get_authorized_client(guest_user)
        await guest_client.post(f"/servers/{str(server1.pk)}/join")
        await guest_client.post(f"/servers/{str(server2.pk)}/join")

        response = await guest_client.get(f"/channels/{str(channel1.id)}/messages")
        assert response.status_code == 200

        response = await guest_client.get(f"/channels/{str(channel2.id)}/messages")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_public_channel_default_not_read(
        self, app: FastAPI, db: Database, client: AsyncClient, current_user: User, server_channel: Channel
    ):
        response = await client.get(f"/channels/{str(server_channel.id)}/messages")
        assert response.status_code == 403

        data = {"content": "gm!", "server": str(server_channel.server.pk), "channel": str(server_channel.id)}
        response = await client.post("/messages", json=data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_public_channel_read_not_write(
        self, app: FastAPI, db: Database, client: AsyncClient, current_user: User, server_channel: Channel
    ):
        await update_item(
            item=server_channel,
            data={"permission_overwrites": [{"group": "@public", "permissions": ["messages.list"]}]},
        )

        response = await client.get(f"/channels/{str(server_channel.id)}/messages")
        assert response.status_code == 200

        data = {"content": "gm!", "server": str(server_channel.server.pk), "channel": str(server_channel.id)}
        response = await client.post("/messages", json=data)
        assert response.status_code == 401
