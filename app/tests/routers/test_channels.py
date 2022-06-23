import binascii
import datetime
import secrets
from typing import Callable

import arrow
import pytest
from eth_account import Account
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.app import App
from app.models.channel import Channel
from app.models.section import Section
from app.models.server import Server
from app.models.user import User
from app.models.webhook import Webhook
from app.schemas.channels import ServerChannelCreateSchema
from app.schemas.messages import MessageCreateSchema, WebhookMessageCreateSchema
from app.schemas.sections import SectionCreateSchema
from app.schemas.servers import ServerCreateSchema
from app.services.channels import create_server_channel, get_dm_channels
from app.services.crud import create_item, get_item, get_item_by_id
from app.services.messages import create_message, create_webhook_message
from app.services.servers import create_server, get_user_servers
from app.services.users import get_user_by_id, get_user_by_wallet_address


class TestChannelsRoutes:
    @pytest.mark.asyncio
    async def test_create_dm_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        members = []
        for x in range(3):
            user = User(wallet_address=f"0x{x}")
            await user.commit()
            members.append(user)

        data = {"kind": "dm", "members": [str(member.id) for member in members]}

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == data["kind"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert "members" in json_response
        assert all([member in json_response["members"] for member in data["members"]])
        assert str(current_user.id) in json_response["members"]

    @pytest.mark.asyncio
    async def test_create_personal_dm_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        data = {"kind": "dm", "members": []}

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == data["kind"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert "members" in json_response
        assert str(current_user.id) in json_response["members"]

    @pytest.mark.asyncio
    async def test_create_multiple_personal_dm_channels(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        data = {"kind": "dm", "members": []}

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == data["kind"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert "members" in json_response
        assert str(current_user.id) in json_response["members"]
        channel_id = json_response["id"]

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response["id"] == channel_id

    @pytest.mark.asyncio
    async def test_create_server_channel(
        self, app: FastAPI, db: Database, current_user: User, server: Server, authorized_client: AsyncClient
    ):
        data = {
            "kind": "server",
            "name": "fancy-announcements",
            "server": str(server.id),
        }

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == data["kind"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert "name" in json_response
        assert json_response["name"] == data["name"]
        assert "server" in json_response
        assert json_response["server"] == str(server.id)

    @pytest.mark.asyncio
    async def test_create_server_channel_not_belong_to_server(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        server: Server,
        authorized_client: AsyncClient,
        create_new_user: Callable,
        get_authorized_client: Callable,
    ):
        data = {
            "kind": "server",
            "name": "fancy-announcements",
            "server": str(server.id),
        }
        member = await create_new_user()
        member_auth_client = await get_authorized_client(member)

        response = await member_auth_client.post("/channels", json=data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_server_channel_not_owner(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        server: Server,
        authorized_client: AsyncClient,
        create_new_user: Callable,
        get_authorized_client: Callable,
    ):
        data = {
            "kind": "server",
            "name": "fancy-announcements",
            "server": str(server.id),
        }
        member = await create_new_user()
        member_auth_client = await get_authorized_client(member)

        response = await member_auth_client.post(f"/servers/{str(server.pk)}/join")
        assert response.status_code == 201

        response = await member_auth_client.post("/channels", json=data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_server_channel_with_emojis(
        self, app: FastAPI, db: Database, current_user: User, server: Server, authorized_client: AsyncClient
    ):
        data = {
            "kind": "server",
            "name": "📣-fancy-announcements",
            "server": str(server.id),
        }

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == data["kind"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert "name" in json_response
        assert json_response["name"] == data["name"]
        assert "server" in json_response
        assert json_response["server"] == str(server.id)

    @pytest.mark.asyncio
    async def test_delete_channel_ok(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server, server_channel: Channel
    ):
        response = await authorized_client.delete(f"/channels/{str(server_channel.id)}")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["id"] == str(server_channel.id)
        assert json_response["name"] == server_channel.name
        assert json_response["server"] == str(server.id)
        assert json_response["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_channel_in_section(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server, server_channel: Channel
    ):
        section = await create_item(
            item=SectionCreateSchema(name="test", server=str(server.pk)), result_obj=Section, user_field=None
        )
        section_updates = [{"id": str(section.pk), "channels": [str(server_channel.pk)]}]
        response = await authorized_client.put(f"/servers/{str(server.pk)}/sections", json=section_updates)
        assert response.status_code == 200

        channel_section = await get_item(filters={"channels": server_channel.pk}, result_obj=Section)
        assert channel_section == section

        response = await authorized_client.delete(f"/channels/{str(server_channel.id)}")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["deleted"] is True

        channel_section = await get_item(filters={"channels": server_channel.pk}, result_obj=Section)
        assert channel_section is None

    @pytest.mark.asyncio
    async def test_delete_dm_channel(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server, dm_channel: Channel
    ):
        response = await authorized_client.delete(f"/channels/{str(dm_channel.id)}")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_channel_no_permission(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        guest_user: User,
    ):
        server = await create_server(ServerCreateSchema(name="test Server"), current_user=guest_user)
        new_channel = Channel(server=server.id, owner=guest_user.id, kind="server")
        await new_channel.commit()

        response = await authorized_client.delete(f"/channels/{str(new_channel.id)}")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_server_channel_ok(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        server_channel: Channel,
    ):
        data = {"name": "my-channel!"}
        response = await authorized_client.patch(f"/channels/{str(server_channel.pk)}", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["name"] == data["name"]

    @pytest.mark.asyncio
    async def test_update_dm_channel_ok(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        dm_channel: Channel,
    ):
        data = {"name": "kool & the gang"}
        response = await authorized_client.patch(f"/channels/{str(dm_channel.pk)}", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["name"] == data["name"]

    @pytest.mark.asyncio
    async def test_update_server_channel_as_guest_fails(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        server_channel: Channel,
        create_new_user: Callable,
        get_authorized_client: Callable,
    ):
        member = await create_new_user()
        member_auth_client = await get_authorized_client(member)

        data = {"name": "my-channel!"}
        response = await member_auth_client.patch(f"/channels/{str(server_channel.pk)}", json=data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_dm_channel_as_non_member_fails(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        dm_channel: Channel,
        create_new_user: Callable,
        get_authorized_client: Callable,
    ):
        member = await create_new_user()
        member_auth_client = await get_authorized_client(member)

        data = {"name": "my-channel!"}
        response = await member_auth_client.patch(f"/channels/{str(dm_channel.pk)}", json=data)
        assert response.status_code == 403

    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_update_dm_channel_remove_member_as_not_owner(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        create_new_user: Callable,
        get_authorized_client: Callable,
    ):
        guest = await create_new_user()
        guest_client = await get_authorized_client(guest)

        members = [current_user, guest]
        data = {"kind": "dm", "members": [str(member.id) for member in members]}

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        channel_id = response.json().get("id")

        data = {"members": [str(guest.id)]}
        response = await guest_client.patch(f"/channels/{channel_id}", json=data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_mark_channel_as_read(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        server_channel: Channel,
    ):
        response = await authorized_client.get("/users/me/read_states")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 0

        response = await authorized_client.post(f"/channels/{str(server_channel.pk)}/ack")
        assert response.status_code == 204

        response = await authorized_client.get("/users/me/read_states")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 1
        last_read_at = json_response[0]["last_read_at"]
        diff = arrow.utcnow() - arrow.get(last_read_at)
        assert diff.total_seconds() <= 1

    @pytest.mark.asyncio
    async def test_mark_channel_as_read_specific_ts(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        server_channel: Channel,
    ):
        response = await authorized_client.get("/users/me/read_states")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 0

        mark_read_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=10)
        response = await authorized_client.post(
            f"/channels/{str(server_channel.pk)}/ack?last_read_at={mark_read_at.isoformat()}"
        )
        assert response.status_code == 204

        response = await authorized_client.get("/users/me/read_states")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 1
        last_read_at = json_response[0]["last_read_at"]
        assert arrow.get(last_read_at).timestamp() == pytest.approx(mark_read_at.timestamp(), 0.001)

    @pytest.mark.asyncio
    async def test_bulk_mark_channels_as_read(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        server_channel: Channel,
    ):
        response = await authorized_client.get("/users/me/read_states")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 0

        data = {"channels": [str(server_channel.pk)]}
        response = await authorized_client.post("/channels/ack", json=data)
        assert response.status_code == 204

        response = await authorized_client.get("/users/me/read_states")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 1
        last_read_at = json_response[0]["last_read_at"]
        diff = arrow.utcnow() - arrow.get(last_read_at)
        assert diff.total_seconds() <= 1

    @pytest.mark.asyncio
    async def test_bulk_mark_channels_as_read_specific_ts(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
        server_channel: Channel,
    ):
        response = await authorized_client.get("/users/me/read_states")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 0

        mark_read_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=10)
        data = {"channels": [str(server_channel.pk)], "last_read_at": mark_read_at.isoformat()}
        response = await authorized_client.post("/channels/ack", json=data)
        assert response.status_code == 204

        response = await authorized_client.get("/users/me/read_states")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 1
        last_read_at = json_response[0]["last_read_at"]
        assert arrow.get(last_read_at).timestamp() == pytest.approx(mark_read_at.timestamp(), 0.001)

    @pytest.mark.asyncio
    async def test_bulk_mark_multiple_channels_as_read(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        server: Server,
    ):
        no_channels = 5
        channels = []
        for index, _ in enumerate(range(no_channels)):
            channel_schema = ServerChannelCreateSchema(server=str(server.pk), name=f"random-{index}")
            channel = await create_item(
                item=channel_schema, result_obj=Channel, current_user=current_user, user_field="owner"
            )
            channels.append(channel)

        response = await authorized_client.get("/users/me/read_states")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 0

        data = {"channels": [str(channel.pk) for channel in channels]}
        response = await authorized_client.post("/channels/ack", json=data)
        assert response.status_code == 204

        response = await authorized_client.get("/users/me/read_states")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == no_channels
        now = arrow.utcnow()
        default_ts = None
        for read_state in json_response:
            last_read_at = read_state["last_read_at"]
            diff = now - arrow.get(last_read_at)
            assert diff.total_seconds() <= 1
            if default_ts:
                assert last_read_at == default_ts
            else:
                default_ts = last_read_at

    @pytest.mark.asyncio
    async def test_fetch_channel_messages(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
    ):
        channel1_model = ServerChannelCreateSchema(kind="server", server=str(server.id), name="channel1")
        channel1 = await create_server_channel(channel_model=channel1_model, current_user=current_user)

        channel2_model = ServerChannelCreateSchema(kind="server", server=str(server.id), name="channel2")
        channel2 = await create_server_channel(channel_model=channel2_model, current_user=current_user)

        channel1_msgs = []
        channel1_len = 3
        for _ in range(channel1_len):
            message_model = MessageCreateSchema(server=str(server.id), channel=str(channel1.pk), content="hey")
            message = await create_message(message_model=message_model, current_user=current_user)
            channel1_msgs.append(message)
        channel1_msgs_ids = [str(msg.pk) for msg in channel1_msgs]

        channel2_msgs = []
        channel2_len = 1
        for _ in range(channel2_len):
            message_model = MessageCreateSchema(server=str(server.id), channel=str(channel2.pk), content="hey")
            message = await create_message(message_model=message_model, current_user=current_user)
            channel2_msgs.append(message)
        channel2_msgs_ids = [str(msg.pk) for msg in channel2_msgs]

        response = await authorized_client.get(f"/channels/{str(channel1.pk)}/messages")
        assert response.status_code == 200
        json_response = response.json()
        assert len(response.json()) == channel1_len
        resp_channels = [msg.get("channel") for msg in json_response]
        assert all([channel_id == str(channel1.pk) for channel_id in resp_channels])
        assert all([msg.get("id") in channel1_msgs_ids for msg in json_response])

        response = await authorized_client.get(f"/channels/{str(channel2.pk)}/messages")
        assert response.status_code == 200
        json_response = response.json()
        assert len(response.json()) == channel2_len
        resp_channels = [msg.get("channel") for msg in json_response]
        assert all([channel_id == str(channel2.pk) for channel_id in resp_channels])
        assert all([msg.get("id") in channel2_msgs_ids for msg in json_response])

    @pytest.mark.asyncio
    async def test_create_dm_channel_with_wallets(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        wallets = [current_user.wallet_address]
        for x in range(3):
            key = secrets.token_bytes(32)
            priv = binascii.hexlify(key).decode("ascii")
            private_key = "0x" + priv
            acct = Account.from_key(private_key)
            wallets.append(acct.address)

        data = {"kind": "dm", "members": wallets}

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == data["kind"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert "members" in json_response
        assert str(current_user.id) in json_response["members"]
        for user_id in json_response["members"]:
            user = await get_user_by_id(user_id=user_id)
            assert user.wallet_address in data["members"]

    @pytest.mark.asyncio
    async def test_create_dm_channel_with_wallets_mix(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        members = []
        for x in range(2):
            key = secrets.token_bytes(32)
            priv = binascii.hexlify(key).decode("ascii")
            private_key = "0x" + priv
            acct = Account.from_key(private_key)
            members.append(acct.address)

        for x in range(3):
            user = User(wallet_address=f"0x{x}")
            await user.commit()
            members.append(str(user.pk))

        data = {"kind": "dm", "members": members}

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == data["kind"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert "members" in json_response
        assert len(json_response["members"]) == len(members) + 1
        assert str(current_user.id) in json_response["members"]
        for user_id in json_response["members"][1:]:
            user = await get_user_by_id(user_id=user_id)
            assert user.wallet_address in data["members"] or str(user.pk) in data["members"]

    @pytest.mark.asyncio
    async def test_create_dm_with_wallet_shows_on_signup(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        server: Server,
        client: AsyncClient,
        authorized_client: AsyncClient,
        create_new_user: Callable,
        get_authorized_client: Callable,
        get_signed_message_data: Callable,
    ):
        key = secrets.token_bytes(32)
        priv = binascii.hexlify(key).decode("ascii")
        private_key = "0x" + priv
        acct = Account.from_key(private_key)
        new_user_wallet_addr = acct.address

        members = [str(current_user.pk), new_user_wallet_addr]
        data = {"kind": "dm", "members": members}

        # create DM with non-user address
        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == "dm"
        assert len(json_response.get("members")) == 2

        guest_user = await get_user_by_wallet_address(wallet_address=new_user_wallet_addr)
        assert guest_user is not None

        dm_channels = await get_dm_channels(current_user=guest_user)
        assert len(dm_channels) == 1

        user_servers = await get_user_servers(current_user=guest_user)
        assert len(user_servers) == 0

        data = await get_signed_message_data(private_key, new_user_wallet_addr)
        response = await client.post("/auth/login", json=data)
        assert response.status_code == 201

        user_servers = await get_user_servers(current_user=guest_user)
        assert len(user_servers) == 1

    @pytest.mark.asyncio
    async def test_fetch_channel_messages_with_webhooks(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        integration_app: App,
        integration_app_webhook: Webhook,
    ):
        message_model = MessageCreateSchema(server=str(server.id), channel=str(server_channel.pk), content="hey")
        await create_message(message_model=message_model, current_user=current_user)

        wh_message_model = WebhookMessageCreateSchema(
            webhook=str(integration_app_webhook.pk),
            app=str(integration_app.pk),
            content="webhook message!",
            channel=str(integration_app_webhook.channel.pk),
        )
        await create_webhook_message(message_model=wh_message_model)

        response = await authorized_client.get(f"/channels/{str(server_channel.pk)}/messages")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 2

        wh_message = json_response[0]
        assert wh_message.get("type") == 2
        assert wh_message.get("author") is None
        assert wh_message.get("app") == str(integration_app.pk)
        assert wh_message.get("webhook") == str(integration_app_webhook.pk)

        normal_message = json_response[1]
        assert normal_message.get("type") == 0
        assert normal_message.get("author") == str(current_user.pk)
        assert "app" not in normal_message
        assert "webhook" not in normal_message

    @pytest.mark.asyncio
    async def test_create_topic_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient
    ):
        data = {"kind": "topic", "name": "my-fav-channel"}
        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "kind" in json_response
        assert json_response["kind"] == data["kind"]
        assert "owner" in json_response
        assert json_response["owner"] == str(current_user.id)
        assert "name" in json_response
        assert json_response["name"] == data["name"]
        assert "members" in json_response
        assert len(json_response["members"]) == 1
        assert json_response["members"][0] == str(current_user.pk)

    @pytest.mark.asyncio
    async def test_invite_member_to_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, topic_channel: Channel
    ):
        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 1
        assert tc.members[0] == current_user
        test_wallet_add = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        data = {"members": [test_wallet_add]}
        response = await authorized_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=data)
        assert response.status_code == 204

        test_user = await get_item(filters={"wallet_address": test_wallet_add}, result_obj=User)
        assert test_user is not None

        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 2
        assert tc.members[0] == current_user
        assert tc.members[1] == test_user

    @pytest.mark.asyncio
    async def test_invite_multiple_members_to_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, topic_channel: Channel
    ):
        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 1
        assert tc.members[0] == current_user

        tw1 = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        tw2 = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96044"
        tw3 = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96043"

        data = {"members": [tw1, tw2, tw3]}
        response = await authorized_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=data)
        assert response.status_code == 204

        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 4

    @pytest.mark.asyncio
    async def test_invite_member_to_channel_can_fetch_messages(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        topic_channel: Channel,
        get_authorized_client: Callable,
        create_new_user: Callable,
    ):
        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 1
        assert tc.members[0] == current_user

        member: User = await create_new_user()
        member_client = await get_authorized_client(member)

        response = await member_client.get(f"/channels/{str(topic_channel.pk)}")
        assert response.status_code == 403

        user_client = await get_authorized_client(current_user)
        data = {"members": [member.wallet_address]}
        response = await user_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=data)
        assert response.status_code == 204

        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 2
        assert tc.members[0] == current_user
        assert tc.members[1] == member

        member_client = await get_authorized_client(member)
        response = await member_client.get(f"/channels/{str(topic_channel.pk)}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_invite_twice_member_to_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, topic_channel: Channel
    ):
        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 1
        assert tc.members[0] == current_user
        test_wallet_add = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        data = {"members": [test_wallet_add]}
        response = await authorized_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=data)
        assert response.status_code == 204

        test_user = await get_item(filters={"wallet_address": test_wallet_add}, result_obj=User)
        assert test_user is not None

        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 2
        assert tc.members[0] == current_user
        assert tc.members[1] == test_user

        response = await authorized_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=data)
        assert response.status_code == 204

        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 2
        assert tc.members[0] == current_user
        assert tc.members[1] == test_user

    @pytest.mark.asyncio
    async def test_create_dm_channel_with_same_members_as_topic_channel(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, topic_channel: Channel
    ):
        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 1
        assert tc.members[0] == current_user
        test_wallet_add = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        data = {"members": [test_wallet_add]}
        response = await authorized_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=data)
        assert response.status_code == 204
        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 2

        dm_data = {"kind": "dm", "members": [str(member.pk) for member in tc.members]}
        response = await authorized_client.post("/channels", json=dm_data)
        assert response.status_code == 201
        json_resp = response.json()
        assert json_resp["id"] != str(topic_channel.pk)

    @pytest.mark.asyncio
    async def test_update_topic_channel_avatar(
        self,
        app: FastAPI,
        db: Database,
        authorized_client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
    ):
        data = {
            "name": "kool & the gang",
            "avatar": "https://i.picsum.photos/id/234/536/354.jpg?hmac=xwmMcTiZqMLkn5gOMUyoMQTnrYfX8RrhBpyOpOrIFCE",
        }
        response = await authorized_client.patch(f"/channels/{str(topic_channel.pk)}", json=data)
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["name"] == data["name"]
        assert json_response["avatar"] == data["avatar"]

    @pytest.mark.asyncio
    async def test_make_channel_public(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        topic_channel: Channel,
        get_authorized_client: Callable,
        create_new_user: Callable,
    ):
        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 1
        assert tc.members[0] == current_user

        member: User = await create_new_user()
        member_client = await get_authorized_client(member)

        response = await member_client.get(f"/channels/{str(topic_channel.pk)}")
        assert response.status_code == 403

        user_client = await get_authorized_client(current_user)
        data = [
            {"group": "@public", "permissions": ["channels.view"]},
        ]
        response = await user_client.put(f"/channels/{str(topic_channel.pk)}/permissions", json=data)
        assert response.status_code == 204

        member_client = await get_authorized_client(member)
        response = await member_client.get(f"/channels/{str(topic_channel.pk)}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_kick_myself_from_channel(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        topic_channel: Channel,
        get_authorized_client: Callable,
        create_new_user: Callable,
    ):
        member: User = await create_new_user()

        user_client = await get_authorized_client(current_user)
        data = {"members": [member.wallet_address]}
        response = await user_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=data)
        assert response.status_code == 204

        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 2
        assert tc.members[0] == current_user
        assert tc.members[1] == member

        member_client = await get_authorized_client(member)
        response = await member_client.delete(f"/channels/{str(topic_channel.pk)}/members/me")
        assert response.status_code == 204

        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 1
        assert tc.members[0] == current_user

        response = await member_client.get(f"/channels/{str(topic_channel.pk)}")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_kick_member_from_channel(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        topic_channel: Channel,
        get_authorized_client: Callable,
        create_new_user: Callable,
    ):
        member: User = await create_new_user()

        user_client = await get_authorized_client(current_user)
        data = {"members": [member.wallet_address]}
        response = await user_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=data)
        assert response.status_code == 204

        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 2
        assert tc.members[0] == current_user
        assert tc.members[1] == member

        member_client = await get_authorized_client(member)
        response = await member_client.get(f"/channels/{str(topic_channel.pk)}")
        assert response.status_code == 200

        user_client = await get_authorized_client(current_user)
        response = await user_client.delete(f"/channels/{str(topic_channel.pk)}/members/{str(member.pk)}")
        assert response.status_code == 204

        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 1
        assert tc.members[0] == current_user

        member_client = await get_authorized_client(member)
        response = await member_client.get(f"/channels/{str(topic_channel.pk)}")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_kick_member_from_channel_as_guest_nok(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        topic_channel: Channel,
        get_authorized_client: Callable,
        create_new_user: Callable,
    ):
        member: User = await create_new_user()

        user_client = await get_authorized_client(current_user)
        data = {"members": [member.wallet_address]}
        response = await user_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=data)
        assert response.status_code == 204

        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 2
        assert tc.members[0] == current_user
        assert tc.members[1] == member

        member_client = await get_authorized_client(member)
        response = await member_client.delete(f"/channels/{str(topic_channel.pk)}/members/{str(current_user.pk)}")
        assert response.status_code == 403

        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 2
        assert tc.members[0] == current_user
        assert tc.members[1] == member

    @pytest.mark.asyncio
    async def test_kick_channel_owner_from_channel(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        topic_channel: Channel,
    ):
        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 1
        assert tc.members[0] == current_user

        response = await authorized_client.delete(f"/channels/{str(topic_channel.pk)}/members/me")
        assert response.status_code == 400

        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 1
        assert tc.members[0] == current_user

    @pytest.mark.asyncio
    async def test_delete_topic_channel_ok(
        self, app: FastAPI, db: Database, authorized_client: AsyncClient, server: Server, topic_channel: Channel
    ):
        response = await authorized_client.delete(f"/channels/{str(topic_channel.pk)}")
        assert response.status_code == 200
        json_response = response.json()
        assert json_response["id"] == str(topic_channel.pk)
        assert json_response["name"] == topic_channel.name
        assert json_response["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_topic_channel_with_multiple_members_nok(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        topic_channel: Channel,
        create_new_user: Callable,
    ):
        member = await create_new_user()
        data = {"members": [member.wallet_address]}
        response = await authorized_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=data)
        assert response.status_code == 204

        tc = await get_item_by_id(id_=topic_channel.pk, result_obj=Channel)
        assert len(tc.members) == 2
        assert tc.members[0] == current_user
        assert tc.members[1] == member

        response = await authorized_client.delete(f"/channels/{str(topic_channel.pk)}")
        assert response.status_code == 403
