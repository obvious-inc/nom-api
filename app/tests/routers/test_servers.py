from datetime import datetime, timezone
from typing import Callable

import pytest
from bson import ObjectId
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.helpers.cache_utils import cache
from app.models.channel import Channel
from app.models.section import Section
from app.models.server import Server, ServerJoinRule, ServerMember
from app.models.user import User
from app.schemas.channels import DMChannelCreateSchema, ServerChannelCreateSchema
from app.schemas.sections import SectionCreateSchema
from app.schemas.servers import ServerCreateSchema
from app.schemas.users import UserCreateSchema
from app.services.channels import create_dm_channel, create_server_channel
from app.services.crud import create_item, get_item, get_items, update_item
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

        members = await get_items({"server": ObjectId(json_response["id"])}, result_obj=ServerMember, limit=None)
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
    async def test_list_public_servers_not_empty(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server
    ):
        response = await authorized_client.get("/servers")
        assert response.status_code == 200
        resp_servers = response.json()
        assert len(resp_servers) == 1
        resp_server = resp_servers[0]
        assert resp_server["id"] == str(server.id)
        assert resp_server["member_count"] == 1

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

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)

        assert member is not None
        assert member.user == guest_user

    @pytest.mark.asyncio
    async def test_join_server_allowlist_rules_nok(
        self, app: FastAPI, db: Database, server: Server, guest_user: User, get_authorized_client: Callable
    ):
        rule = ServerJoinRule(type="allowlist", allowlist_addresses=[])
        await rule.commit()
        updated_server = await update_item(server, data={"join_rules": [rule]})
        assert len(updated_server.join_rules) == 1

        server_id = str(server.id)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{server_id}/join")
        assert response.status_code == 403

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)
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
        updated_server = await update_item(server, data={"join_rules": [rule]})
        assert len(updated_server.join_rules) == 1

        server_id = str(server.id)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{server_id}/join")
        assert response.status_code == 201

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)

        assert member is not None
        assert member.user == guest_user

    @pytest.mark.asyncio
    async def test_join_server_guild_rules_ok(
        self, app: FastAPI, db: Database, server: Server, guest_user: User, get_authorized_client: Callable
    ):
        rule = ServerJoinRule(type="guild_xyz", guild_xyz_id="1985")  # everyone has access to this guild
        await rule.commit()
        updated_server = await update_item(server, data={"join_rules": [rule]})
        assert len(updated_server.join_rules) == 1

        server_id = str(server.id)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{server_id}/join")
        assert response.status_code == 201

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)
        assert member is not None
        assert member.user == guest_user

    @pytest.mark.asyncio
    async def test_join_server_guild_rules_nok(
        self, app: FastAPI, db: Database, server: Server, guest_user: User, get_authorized_client: Callable
    ):
        rule = ServerJoinRule(type="guild_xyz", guild_xyz_id="1898")
        await rule.commit()
        updated_server = await update_item(server, data={"join_rules": [rule]})
        assert len(updated_server.join_rules) == 1

        server_id = str(server.id)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{server_id}/join")
        assert response.status_code == 403

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)
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
        updated_server = await update_item(server, data={"join_rules": [allowlist_rule, guild_rule]})
        assert len(updated_server.join_rules) == 2

        server_id = str(server.id)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{server_id}/join")
        assert response.status_code == 201

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)

        assert member is not None
        assert member.user == guest_user

    @pytest.mark.skip("Not using guild.xyz at the moment")
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
        updated_server = await update_item(server, data={"join_rules": [allowlist_rule, guild_rule]})
        assert len(updated_server.join_rules) == 2

        server_id = str(server.id)
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post(f"/servers/{server_id}/join")
        assert response.status_code == 201

        member = await get_item(filters={"server": server.pk, "user": guest_user.pk}, result_obj=ServerMember)

        assert member is not None
        assert member.user == guest_user

    @pytest.mark.asyncio
    async def test_create_server_has_default_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        server_name = "test"
        response = await authorized_client.post("/servers", json={"name": server_name})
        assert response.status_code == 201
        json_response = response.json()
        server_id = json_response["id"]

        response = await authorized_client.get(f"/servers/{server_id}/channels")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 1
        assert json_response[0]["name"] == "lounge"  # TODO: configurable

    @pytest.mark.asyncio
    async def test_create_server_with_description_avatar(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        data = {"name": "test", "description": "This is just a test server", "avatar": "https://image"}

        response = await authorized_client.post("/servers", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "name" in json_response
        assert "id" in json_response
        assert json_response["id"] is not None
        assert json_response["name"] == data["name"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert json_response["description"] == data["description"]
        assert json_response["avatar"] == data["avatar"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "initial_data, final_data",
        [
            ({"name": "test", "description": "test"}, {}),
            ({"name": "test", "description": "test"}, {"name": "new name"}),
            ({"name": "test", "description": "test"}, {"description": "this is a test server"}),
            ({"name": "test"}, {"description": "this is a test server", "avatar": "https://image"}),
        ],
    )
    async def test_update_server(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, initial_data, final_data
    ):
        response = await authorized_client.post("/servers", json=initial_data)
        assert response.status_code == 201
        original_response = response.json()
        for field, value in initial_data.items():
            assert original_response[field] == value

        server_id = original_response["id"]

        response = await authorized_client.patch(f"/servers/{server_id}", json=final_data)
        assert response.status_code == 200
        json_response = response.json()
        for field, value in json_response.items():
            if field in final_data:
                assert json_response[field] == final_data[field]
            else:
                assert json_response[field] == original_response[field]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "rules, is_eligible",
        [
            ([], True),
            ([{"type": "allowlist", "allowlist_addresses": []}], False),
            ([{"type": "guild_xyz", "guild_xyz_id": "1985"}], True),
            ([{"type": "guild_xyz", "guild_xyz_id": "1898"}], False),
        ],
    )
    async def test_is_eligible_for_server(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, rules, is_eligible
    ):
        data = {"name": "test"}
        response = await authorized_client.post("/servers", json=data)
        assert response.status_code == 201
        json_response = response.json()
        server_id = json_response["id"]

        response = await authorized_client.patch(f"/servers/{server_id}", json={"join_rules": rules})
        assert response.status_code == 200

        response = await authorized_client.get(f"/servers/{server_id}/eligible")
        if is_eligible:
            assert response.status_code == 204
        else:
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_is_eligible_for_server_in_allowlist_addresses(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        data = {"name": "test"}
        response = await authorized_client.post("/servers", json=data)
        assert response.status_code == 201
        json_response = response.json()
        server_id = json_response["id"]

        response = await authorized_client.patch(
            f"/servers/{server_id}",
            json={"join_rules": [{"type": "allowlist", "allowlist_addresses": [str(current_user.wallet_address)]}]},
        )
        assert response.status_code == 200

        response = await authorized_client.get(f"/servers/{server_id}/eligible")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_update_server_system_channel_ok(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        channel_model = ServerChannelCreateSchema(kind="server", server=str(server.id), name="entrance")
        channel = await create_server_channel(channel_model=channel_model, current_user=current_user)

        patch_data = {"system_channel": str(channel.pk)}
        response = await authorized_client.patch(f"/servers/{str(server.pk)}", json=patch_data)
        assert response.status_code == 200

        await server.reload()
        assert server.system_channel == channel

    @pytest.mark.asyncio
    async def test_update_server_system_channel_wrong_server(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        other_server_model = ServerCreateSchema(name="Other")
        other_server = await create_server(other_server_model, current_user=current_user)
        channel_model = ServerChannelCreateSchema(kind="server", server=str(other_server.id), name="entrance")
        channel = await create_server_channel(channel_model=channel_model, current_user=current_user)

        patch_data = {"system_channel": str(channel.pk)}
        response = await authorized_client.patch(f"/servers/{str(server.pk)}", json=patch_data)
        assert response.status_code == 403

        await server.reload()
        assert server.system_channel != channel

    @pytest.mark.asyncio
    async def test_update_server_system_channel_with_dm(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        channel_model = DMChannelCreateSchema(kind="dm", members=[str(current_user.pk)])
        channel = await create_dm_channel(channel_model, current_user=current_user)

        patch_data = {"system_channel": str(channel.pk)}
        response = await authorized_client.patch(f"/servers/{str(server.pk)}", json=patch_data)
        assert response.status_code == 403

        await server.reload()
        assert server.system_channel != channel

    @pytest.mark.asyncio
    async def test_get_server_sections(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        response = await authorized_client.get(f"/servers/{str(server.pk)}/sections")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_create_section_empty(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        response = await authorized_client.get(f"/servers/{str(server.pk)}/sections")
        assert response.status_code == 200
        assert response.json() == []

        new_section_data = {"name": "community"}
        response = await authorized_client.post(f"/servers/{str(server.pk)}/sections", json=new_section_data)
        assert response.status_code == 201

        response = await authorized_client.get(f"/servers/{str(server.pk)}/sections")
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_update_all_sections(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        section_names = ["community", "dao", "offtopic"]
        sections = []
        for name in section_names:
            section = await create_item(
                item=SectionCreateSchema(name=name, server=str(server.pk)), result_obj=Section, user_field=None
            )
            sections.append(section)

        channels = []
        for i in range(10):
            channel = await create_server_channel(
                channel_model=ServerChannelCreateSchema(kind="server", server=str(server.id), name=f"channel-{i}"),
                current_user=current_user,
            )
            channels.append(channel)

        section_updates = [
            {
                "id": str(sections[0].pk),
                "name": section_names[0],
                "position": 0,
                "channels": [str(channel.pk) for channel in channels[:3]],
            },
            {
                "id": str(sections[1].pk),
                "name": section_names[1],
                "position": 1,
                "channels": [str(channel.pk) for channel in channels[3:7]],
            },
            {
                "id": str(sections[2].pk),
                "name": section_names[2],
                "position": 2,
                "channels": [str(channel.pk) for channel in channels[7:]],
            },
        ]

        response = await authorized_client.put(f"/servers/{str(server.pk)}/sections", json=section_updates)
        assert response.status_code == 200

        response = await authorized_client.get(f"/servers/{str(server.pk)}/sections")
        assert response.status_code == 200
        resp_sections = response.json()
        assert len(resp_sections) == 3
        for i in range(3):
            assert resp_sections[i]["name"] == section_updates[i]["name"]
            assert resp_sections[i]["channels"] == section_updates[i]["channels"]

    @pytest.mark.asyncio
    async def test_update_sections_remove_channel_from_section(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
    ):
        section = await create_item(
            item=SectionCreateSchema(name="test", server=str(server.pk)), result_obj=Section, user_field=None
        )
        section_updates = [{"id": str(section.pk), "channels": [str(server_channel.pk)]}]
        response = await authorized_client.put(f"/servers/{str(server.pk)}/sections", json=section_updates)
        assert response.status_code == 200

        cached_section_id = await cache.client.hget(f"channel:{str(server_channel.pk)}", "section")
        assert cached_section_id == str(section.pk)

        section_updates = [{"id": str(section.pk), "channels": []}]
        response = await authorized_client.put(f"/servers/{str(server.pk)}/sections", json=section_updates)
        assert response.status_code == 200

        cached_section_id = await cache.client.hget(f"channel:{str(server_channel.pk)}", "section")
        assert cached_section_id == ""

    @pytest.mark.asyncio
    async def test_update_all_sections_order(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        section_names = ["community", "dao", "offtopic"]
        sections = []
        for name in section_names:
            section = await create_item(
                item=SectionCreateSchema(name=name, server=str(server.pk)), result_obj=Section, user_field=None
            )
            sections.append(section)

        channels = []
        for i in range(10):
            channel = await create_server_channel(
                channel_model=ServerChannelCreateSchema(kind="server", server=str(server.id), name=f"channel-{i}"),
                current_user=current_user,
            )
            channels.append(channel)

        section_updates = [
            {
                "id": str(sections[0].pk),
                "name": section_names[0],
                "position": 0,
                "channels": [str(channel.pk) for channel in channels[:3]],
            },
            {
                "id": str(sections[1].pk),
                "name": section_names[1],
                "position": 1,
                "channels": [str(channel.pk) for channel in channels[3:7]],
            },
            {
                "id": str(sections[2].pk),
                "name": section_names[2],
                "position": 2,
                "channels": [str(channel.pk) for channel in channels[7:]],
            },
        ]

        response = await authorized_client.put(f"/servers/{str(server.pk)}/sections", json=section_updates)
        assert response.status_code == 200

        response = await authorized_client.get(f"/servers/{str(server.pk)}/sections")
        assert response.status_code == 200
        resp_sections = response.json()
        assert len(resp_sections) == 3
        for i in range(3):
            assert resp_sections[i]["name"] == section_updates[i]["name"]
            assert resp_sections[i]["channels"] == section_updates[i]["channels"]

        update_sections = [
            {
                "id": str(sections[2].pk),
                "name": section_names[2],
                "position": 1,
                "channels": [str(channel.pk) for channel in channels[7:]],
            },
            {
                "id": str(sections[1].pk),
                "name": section_names[1],
                "position": 0,
                "channels": [str(channel.pk) for channel in channels[3:7]],
            },
            {
                "id": str(sections[0].pk),
                "name": section_names[0],
                "position": 2,
                "channels": [str(channel.pk) for channel in channels[:3]],
            },
        ]

        response = await authorized_client.put(f"/servers/{str(server.pk)}/sections", json=update_sections)
        assert response.status_code == 200

        response = await authorized_client.get(f"/servers/{str(server.pk)}/sections")
        assert response.status_code == 200
        resp_sections = response.json()
        assert len(resp_sections) == 3
        for section in resp_sections:
            section_position = section["position"]
            for update in update_sections:
                if section_position == update["position"]:
                    assert section["name"] == update["name"]
                    assert section["channels"] == update["channels"]

    @pytest.mark.asyncio
    async def test_fetch_server_info(self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server):
        response = await authorized_client.get(f"/servers/{str(server.pk)}")
        assert response.status_code == 200
        json_server = response.json()
        assert json_server["id"] == str(server.id)
        assert json_server["member_count"] == 1
