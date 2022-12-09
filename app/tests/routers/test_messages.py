import asyncio
import random
from typing import Callable

import arrow
import pytest
from bson import ObjectId
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.helpers.message_utils import blockify_content, get_message_mentions
from app.helpers.whitelist import whitelist_wallet
from app.models.app import App
from app.models.channel import Channel
from app.models.message import Message, MessageReaction
from app.models.server import Server
from app.models.user import User
from app.models.webhook import Webhook
from app.schemas.messages import MessageCreateSchema, WebhookMessageCreateSchema
from app.services.crud import create_item, get_item_by_id
from app.services.messages import create_app_message, get_messages


class TestMessagesRoutes:
    @pytest.mark.asyncio
    async def test_create_message(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
    ):
        data = {"content": "gm!", "server": str(server.id), "channel": str(server_channel.id)}
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "content" in json_response
        assert json_response["content"] == data["content"]
        assert json_response["server"] == data["server"] == str(server.id)
        assert json_response["channel"] == data["channel"] == str(server_channel.id)

    @pytest.mark.asyncio
    async def test_add_reaction_to_message(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
    ):
        messages = await get_messages(channel_id=str(server_channel.id), limit=100)
        assert len(messages) == 1

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message == channel_message
        assert len(message.reactions) == 0

        response = await authorized_client.post(f"/messages/{str(message.id)}/reactions/🙌")
        assert response.status_code == 204

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert len(message.reactions) == 1
        reaction = message.reactions[0]
        assert reaction.emoji == "🙌"
        assert reaction.count == 1
        assert [user.pk for user in reaction.users] == [current_user.id]

    @pytest.mark.asyncio
    async def test_add_same_reaction_to_message(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
        guest_user: User,
    ):
        emoji = "😍"
        channel_message.reactions = [MessageReaction(emoji=emoji, count=1, users=[guest_user.pk])]
        await channel_message.commit()

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message == channel_message
        assert len(message.reactions) == 1

        response = await authorized_client.post(f"/messages/{str(message.id)}/reactions/{emoji}")
        assert response.status_code == 204

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert len(message.reactions) == 1
        reaction = message.reactions[0]
        assert reaction.emoji == emoji
        assert reaction.count == 2
        assert [user.pk for user in reaction.users] == [guest_user.id, current_user.id]

    @pytest.mark.asyncio
    async def test_add_same_user_reaction_to_message(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
        guest_user: User,
    ):
        emoji = "😍"
        channel_message.reactions = [MessageReaction(emoji=emoji, count=1, users=[current_user.pk])]
        await channel_message.commit()

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message == channel_message
        assert len(message.reactions) == 1

        response = await authorized_client.post(f"/messages/{str(message.id)}/reactions/{emoji}")
        assert response.status_code == 204

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert len(message.reactions) == 1
        reaction = message.reactions[0]
        assert reaction.emoji == emoji
        assert reaction.count == 1
        assert [user.pk for user in reaction.users] == [current_user.id]

    @pytest.mark.asyncio
    async def test_add_new_reaction_to_message_with_reactions(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
        guest_user: User,
    ):
        channel_message.reactions = [MessageReaction(emoji="😍", count=1, users=[guest_user.pk])]
        await channel_message.commit()

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message == channel_message
        assert len(message.reactions) == 1

        new_emoji = "💪"
        response = await authorized_client.post(f"/messages/{str(message.id)}/reactions/{new_emoji}")
        assert response.status_code == 204

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert len(message.reactions) == 2
        first_reaction = message.reactions[0]
        assert first_reaction.emoji == "😍"
        assert first_reaction.count == 1
        assert [user.pk for user in first_reaction.users] == [guest_user.id]

        second_reaction = message.reactions[1]
        assert second_reaction.emoji == new_emoji
        assert second_reaction.count == 1
        assert [user.pk for user in second_reaction.users] == [current_user.id]

        response = await authorized_client.get(f"/channels/{str(server_channel.id)}/messages")
        assert response.status_code == 200
        json_response = response.json()
        json_message = json_response[0]
        assert "reactions" in json_message
        assert len(json_message["reactions"]) == 2

    @pytest.mark.asyncio
    async def test_remove_reaction_from_message(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
        guest_user: User,
    ):
        channel_message.reactions = [MessageReaction(emoji="😍", count=1, users=[current_user.pk])]
        await channel_message.commit()

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message == channel_message
        assert len(message.reactions) == 1

        response = await authorized_client.delete(f"/messages/{str(message.id)}/reactions/😍")
        assert response.status_code == 204

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert len(message.reactions) == 0

    @pytest.mark.asyncio
    async def test_remove_reaction_from_message_with_multiple_reactions(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
        guest_user: User,
    ):
        channel_message.reactions = [MessageReaction(emoji="😍", count=2, users=[current_user.pk, guest_user.pk])]
        await channel_message.commit()

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message == channel_message
        assert len(message.reactions) == 1

        response = await authorized_client.delete(f"/messages/{str(message.id)}/reactions/😍")
        assert response.status_code == 204

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert len(message.reactions) == 1
        reaction = message.reactions[0]
        assert reaction.emoji == "😍"
        assert reaction.count == 1
        assert [user.pk for user in reaction.users] == [guest_user.id]

    @pytest.mark.asyncio
    async def test_create_message_update_last_message_at(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
    ):
        data = {"content": "gm", "server": str(server.id), "channel": str(server_channel.id)}
        channel = await get_item_by_id(id_=server_channel.id, result_obj=Channel)
        assert channel.last_message_at is None
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "content" in json_response
        assert json_response["content"] == data["content"]
        assert json_response["server"] == data["server"] == str(server.id)
        assert json_response["channel"] == data["channel"] == str(server_channel.id)

        await asyncio.sleep(random.random())
        channel = await get_item_by_id(id_=server_channel.id, result_obj=Channel)
        assert channel.last_message_at is not None
        created_at = arrow.get(json_response["created_at"])
        last_message_at = arrow.get(channel.last_message_at)
        assert created_at == last_message_at

    @pytest.mark.asyncio
    async def test_delete_message(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
    ):
        messages = await get_messages(channel_id=str(server_channel.id), limit=10)
        assert len(messages) == 1

        response = await authorized_client.delete(f"/messages/{str(channel_message.id)}")
        assert response.status_code == 204

        messages = await get_messages(channel_id=str(server_channel.id), limit=10)
        assert len(messages) == 0

        message = await Message.find_one({"_id": channel_message.pk})
        assert message.deleted is True

    @pytest.mark.asyncio
    async def test_delete_message_from_another_user(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        client: AsyncClient,
        server: Server,
        server_channel: Channel,
        create_new_user: Callable,
        get_authorized_client: Callable,
    ):
        guest_user_1 = await create_new_user()
        guest_user_2 = await create_new_user()

        channel_message = await create_item(
            item=MessageCreateSchema(server=str(server.id), channel=str(server_channel.id), content="hey"),
            result_obj=Message,
            current_user=guest_user_1,
            user_field="author",
        )

        messages = await get_messages(channel_id=str(server_channel.id), limit=10)
        assert len(messages) == 1

        guest_2_client = await get_authorized_client(guest_user_2)
        response = await guest_2_client.delete(f"/messages/{str(channel_message.id)}")
        assert response.status_code == 403

        messages = await get_messages(channel_id=str(server_channel.id), limit=10)
        assert len(messages) == 1

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message.deleted is False

    @pytest.mark.asyncio
    async def test_delete_message_as_server_owner(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        create_new_user: Callable,
    ):
        guest_user = await create_new_user()
        channel_message = await create_item(
            item=MessageCreateSchema(server=str(server.id), channel=str(server_channel.id), content="hey"),
            result_obj=Message,
            current_user=guest_user,
            user_field="author",
        )

        messages = await get_messages(channel_id=str(server_channel.id), limit=10)
        assert len(messages) == 1

        response = await authorized_client.delete(f"/messages/{str(channel_message.id)}")
        assert response.status_code == 204

        messages = await get_messages(channel_id=str(server_channel.id), limit=10)
        assert len(messages) == 0

        message = await Message.find_one({"_id": channel_message.id})
        assert message.deleted is True

    @pytest.mark.asyncio
    async def test_edit_message(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
    ):
        message: Message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message.edited_at is None

        data = {"content": "new message update!"}
        response = await authorized_client.patch(f"/messages/{str(channel_message.id)}", json=data)
        assert response.status_code == 200
        json_response = response.json()

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message is not None
        assert json_response["id"] == str(message.id)
        assert json_response["content"] == message.content == data["content"]
        assert message.edited_at is not None
        assert message.edited_at != message.created_at

    @pytest.mark.asyncio
    async def test_create_message_with_user_mention(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        create_new_user: Callable,
    ):
        guest_user = await create_new_user()
        data = {
            "blocks": [
                {
                    "type": "paragraph",
                    "children": [
                        {"text": "hey "},
                        {"type": "user", "ref": str(guest_user.id)},
                        {"text": " what up"},
                    ],
                }
            ],
            "server": str(server.id),
            "channel": str(server_channel.id),
        }
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message)
        mentions = await get_message_mentions(message)
        assert len(mentions) == 1
        mention_type, mention_ref = mentions[0]
        assert mention_type == "user"
        assert mention_ref == str(guest_user.id)

    @pytest.mark.asyncio
    async def test_create_message_with_user_multiple_mentions(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        create_new_user: Callable,
    ):
        guest_user_1 = await create_new_user()
        guest_user_2 = await create_new_user()

        data = {
            "blocks": [
                {
                    "type": "paragraph",
                    "children": [
                        {"text": "hey"},
                        {"type": "user", "ref": str(guest_user_1.id)},
                        {"text": " and "},
                        {"type": "user", "ref": str(guest_user_2.id)},
                        {"text": " what up?"},
                    ],
                }
            ],
            "server": str(server.id),
            "channel": str(server_channel.id),
        }
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message)
        mentions = await get_message_mentions(message)
        assert len(mentions) == 2
        mention_type, mention_ref = mentions[0]
        assert mention_type == "user"
        assert mention_ref == str(guest_user_1.id)
        mention_type, mention_ref = mentions[1]
        assert mention_type == "user"
        assert mention_ref == str(guest_user_2.id)

    @pytest.mark.asyncio
    async def test_create_message_with_unknown_mention_types(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        create_new_user: Callable,
    ):
        guest_user = await create_new_user()
        data = {
            "blocks": [
                {
                    "type": "paragraph",
                    "children": [
                        {"text": "hey "},
                        {"type": "user", "ref": str(guest_user.id)},
                        {"text": " and "},
                        {"type": "x", "ref": str(ObjectId())},
                        {"text": ", what up?"},
                    ],
                }
            ],
            "server": str(server.id),
            "channel": str(server_channel.id),
        }
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message)
        mentions = await get_message_mentions(message)
        assert len(mentions) == 1
        mention_type, mention_ref = mentions[0]
        assert mention_type == "user"
        assert mention_ref == str(guest_user.id)

    @pytest.mark.asyncio
    async def test_create_message_with_broadcast_mention(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
    ):
        data = {
            "blocks": [
                {
                    "type": "paragraph",
                    "children": [{"text": "hey "}, {"type": "broadcast", "ref": "here"}, {"text": ", what up?"}],
                }
            ],
            "server": str(server.id),
            "channel": str(server_channel.id),
        }
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message)
        mentions = await get_message_mentions(message)
        assert len(mentions) == 1
        mention_type, mention_ref = mentions[0]
        assert mention_type == "broadcast"
        assert mention_ref == "here"

    @pytest.mark.asyncio
    async def test_create_message_with_broadcast_and_user_mentions(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        create_new_user: Callable,
    ):
        guest_user = await create_new_user()
        data = {
            "blocks": [
                {
                    "type": "paragraph",
                    "children": [
                        {"text": "hey "},
                        {"type": "broadcast", "ref": "here"},
                        {"text": " and "},
                        {"type": "user", "ref": str(guest_user.id)},
                        {"text": " what up?"},
                    ],
                }
            ],
            "server": str(server.id),
            "channel": str(server_channel.id),
        }
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message)
        mentions = await get_message_mentions(message)
        assert len(mentions) == 2
        mention_type, mention_ref = mentions[0]
        assert mention_type == "broadcast"
        assert mention_ref == "here"
        mention_type, mention_ref = mentions[1]
        assert mention_type == "user"
        assert mention_ref == str(guest_user.id)

    @pytest.mark.asyncio
    async def test_create_message_blocks_with_user_mentions(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        create_new_user: Callable,
    ):
        guest_user = await create_new_user()
        blocks = [
            {
                "type": "paragraph",
                "children": [
                    {"text": "hey "},
                    {"type": "user", "ref": str(guest_user.id)},
                    {"text": ", you around?"},
                ],
            },
        ]
        data = {"blocks": blocks, "server": str(server.id), "channel": str(server_channel.id)}
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message)
        mentions = await get_message_mentions(message)
        assert len(mentions) == 1
        mention_type, mention_ref = mentions[0]
        assert mention_type == "user"
        assert mention_ref == str(guest_user.id)

    @pytest.mark.asyncio
    async def test_create_message_blocks_with_user_and_broadcast_mentions(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        create_new_user: Callable,
    ):
        guest_user = await create_new_user()
        blocks = [
            {
                "type": "paragraph",
                "children": [
                    {"text": "hey "},
                    {"type": "user", "ref": str(guest_user.id)},
                    {"text": " and "},
                    {"type": "broadcast", "ref": "channel"},
                    {"text": ", you around?"},
                ],
            },
        ]
        data = {"blocks": blocks, "server": str(server.id), "channel": str(server_channel.id)}
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message)
        mentions = await get_message_mentions(message)
        assert len(mentions) == 2
        mention_type, mention_ref = mentions[0]
        assert mention_type == "user"
        assert mention_ref == str(guest_user.id)
        mention_type, mention_ref = mentions[1]
        assert mention_type == "broadcast"
        assert mention_ref == "channel"

    @pytest.mark.asyncio
    async def test_create_message_blocks_with_user_and_broadcast_unknown_mentions(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        create_new_user: Callable,
    ):
        guest_user = await create_new_user()
        blocks = [
            {
                "type": "paragraph",
                "children": [
                    {"text": "hey "},
                    {"type": "user", "ref": str(guest_user.id)},
                    {"text": " and "},
                    {"type": "broadcast", "ref": "unknown"},
                    {"text": ", you around?"},
                ],
            },
        ]
        data = {"blocks": blocks, "server": str(server.id), "channel": str(server_channel.id)}
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message)
        mentions = await get_message_mentions(message)
        assert len(mentions) == 1
        mention_type, mention_ref = mentions[0]
        assert mention_type == "user"
        assert mention_ref == str(guest_user.id)

    @pytest.mark.asyncio
    async def test_create_message_blocks_with_mentions_complex_hierarchy(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        create_new_user: Callable,
    ):
        guest_user_1 = await create_new_user()
        guest_user_2 = await create_new_user()
        blocks = [
            {
                "type": "paragraph",
                "children": [
                    {"text": "hey "},
                    {"type": "user", "ref": str(guest_user_1.id)},
                    {"text": ", you around?"},
                ],
            },
            {
                "type": "list",
                "children": [
                    {
                        "type": "paragraph",
                        "children": [
                            {"text": "inside paragraph mention to "},
                            {"type": "broadcast", "ref": "here"},
                        ],
                    },
                    {"text": "what about you "},
                    {"type": "user", "ref": str(guest_user_2.id)},
                    {"text": "?"},
                ],
            },
        ]
        data = {"blocks": blocks, "server": str(server.id), "channel": str(server_channel.id)}
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message)
        mentions = await get_message_mentions(message)
        assert len(mentions) == 3
        mention_type, mention_ref = mentions[0]
        assert mention_type == "user"
        assert mention_ref == str(guest_user_1.id)
        mention_type, mention_ref = mentions[1]
        assert mention_type == "broadcast"
        assert mention_ref == "here"
        mention_type, mention_ref = mentions[2]
        assert mention_type == "user"
        assert mention_ref == str(guest_user_2.id)

    @pytest.mark.asyncio
    async def test_create_message_with_blocks(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
    ):
        text = "gm!"
        blocks = await blockify_content(content=text)
        data = {"blocks": blocks, "server": str(server.id), "channel": str(server_channel.id)}
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "content" in json_response
        assert "blocks" in json_response
        assert json_response["content"] == text
        assert json_response["blocks"] == blocks
        assert json_response["server"] == data["server"] == str(server.id)
        assert json_response["channel"] == data["channel"] == str(server_channel.id)

    @pytest.mark.asyncio
    async def test_create_message_with_blocks_and_content(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
    ):
        text = "gm!"
        blocks = await blockify_content(content=text)
        # take client's content as final 'content' value
        content = "random stuff"
        data = {"blocks": blocks, "content": content, "server": str(server.id), "channel": str(server_channel.id)}
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "content" in json_response
        assert "blocks" in json_response
        assert json_response["content"] == content
        assert json_response["blocks"] == blocks
        assert json_response["server"] == data["server"] == str(server.id)
        assert json_response["channel"] == data["channel"] == str(server_channel.id)

    @pytest.mark.asyncio
    async def test_edit_message_blocks(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
    ):
        message: Message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message.edited_at is None

        content = "new message update!"
        blocks = await blockify_content(content)
        data = {"blocks": blocks}
        response = await authorized_client.patch(f"/messages/{str(channel_message.id)}", json=data)
        assert response.status_code == 200
        json_response = response.json()

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message is not None
        assert json_response["id"] == str(message.id)
        assert json_response["content"] == message.content == content
        assert json_response["blocks"] == message.blocks == blocks
        assert message.edited_at is not None
        assert message.edited_at != message.created_at

    @pytest.mark.asyncio
    async def test_create_message_without_content_and_blocks_fails(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
    ):
        data = {"server": str(server.id), "channel": str(server_channel.id)}
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_edit_message_with_empty_blocks_fails(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
    ):
        message: Message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message.edited_at is None

        data: dict = {"blocks": []}
        response = await authorized_client.patch(f"/messages/{str(channel_message.id)}", json=data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_edit_message_with_empty_content_fails(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
    ):
        message: Message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message.edited_at is None

        data = {"content": ""}
        response = await authorized_client.patch(f"/messages/{str(channel_message.id)}", json=data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reply_message(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
    ):
        messages = await get_messages(channel_id=str(server_channel.id), limit=10)
        assert len(messages) == 1

        data = {"content": "reply!", "server": str(server.id), "channel": str(server_channel.id)}
        response = await authorized_client.post(f"/messages/{str(channel_message.id)}/replies", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert "content" in json_response
        assert json_response["content"] == data["content"]
        assert json_response["server"] == data["server"] == str(server.id)
        assert json_response["channel"] == data["channel"] == str(server_channel.id)
        assert json_response["reply_to"] == str(channel_message.id)

        messages = await get_messages(channel_id=str(server_channel.id), limit=10)
        assert len(messages) == 2

    @pytest.mark.asyncio
    async def test_create_message_mention_count_increase(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        create_new_user: Callable,
        get_authorized_client: Callable,
        topic_channel: Channel,
    ):
        guest_user = await create_new_user()
        invite_data = {"members": [str(guest_user.pk)]}
        response = await authorized_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=invite_data)
        assert response.status_code == 204

        guest_client = await get_authorized_client(guest_user)

        data = {
            "blocks": [
                {
                    "type": "paragraph",
                    "children": [
                        {"text": "hey "},
                        {"type": "user", "ref": str(current_user.id)},
                        {"text": ", what up?"},
                    ],
                }
            ],
            "channel": str(topic_channel.pk),
        }
        response = await guest_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message)
        mentions = await get_message_mentions(message)
        assert len(mentions) == 1
        mention_type, mention_ref = mentions[0]
        assert mention_type == "user"
        assert mention_ref == str(current_user.id)

        await asyncio.sleep(random.random())
        mentioned_user_client = await get_authorized_client(current_user)
        response = await mentioned_user_client.get("/users/me/read_states")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 1
        assert "mention_count" in json_response[0]
        assert json_response[0]["mention_count"] == 1

    @pytest.mark.skip("No support for group broadcast yet")
    @pytest.mark.asyncio
    async def test_create_message_broadcast_mention_count_increase(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        create_new_user: Callable,
        get_authorized_client: Callable,
    ):
        guest_user = await create_new_user()
        guest_client = await get_authorized_client(guest_user)

        response = await guest_client.post(f"/servers/{str(server.pk)}/join")
        assert response.status_code == 201

        data = {
            "blocks": [
                {
                    "type": "paragraph",
                    "children": [{"text": "hey "}, {"type": "broadcast", "ref": "everyone"}, {"text": ", what up?"}],
                }
            ],
            "server": str(server.id),
            "channel": str(server_channel.id),
        }
        response = await guest_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message)
        mentions = await get_message_mentions(message)
        assert len(mentions) == 1
        mention_type, mention_ref = mentions[0]
        assert mention_type == "broadcast"
        assert mention_ref == "everyone"

        await asyncio.sleep(random.random())
        mentioned_user_client = await get_authorized_client(current_user)
        response = await mentioned_user_client.get("/users/me/read_states")
        assert response.status_code == 200
        json_response = response.json()
        assert len(json_response) == 1
        assert "mention_count" in json_response[0]
        assert json_response[0]["mention_count"] == 1

    @pytest.mark.asyncio
    async def test_get_specific_message(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
        guest_user: User,
    ):
        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message == channel_message

        response = await authorized_client.get(f"/channels/{str(server_channel.id)}/messages/{str(channel_message.id)}")
        assert response.status_code == 200
        json_message = response.json()
        assert json_message["content"] == message.content

    @pytest.mark.asyncio
    async def test_get_specific_webhook_message(
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
        wh_message_model = WebhookMessageCreateSchema(
            webhook=str(integration_app_webhook.pk),
            app=str(integration_app.pk),
            content="webhook message!",
            channel=str(integration_app_webhook.channel.pk),
        )
        wh_message = await create_app_message(message_model=wh_message_model, current_app=integration_app)

        response = await authorized_client.get(f"/channels/{str(server_channel.id)}/messages/{str(wh_message.id)}")
        assert response.status_code == 200
        json_message = response.json()
        assert json_message["content"] == wh_message.content
        assert json_message.get("type") == 2
        assert json_message.get("author") is None
        assert json_message.get("app") == str(integration_app.pk)
        assert json_message.get("webhook") == str(integration_app_webhook.pk)

    @pytest.mark.asyncio
    async def test_delete_message_invalid_id(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
        channel_message: Message,
        guest_user: User,
    ):
        message = await get_item_by_id(id_=channel_message.id, result_obj=Message)
        assert message == channel_message

        response = await authorized_client.delete("/messages/0")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_messages_before_id(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
    ):
        messages = []
        for i in range(10):
            content = f"message {i}"
            msg = await create_item(
                item=MessageCreateSchema(server=str(server.id), channel=str(server_channel.id), content=content),
                result_obj=Message,
                current_user=current_user,
                user_field="author",
            )
            messages.append(msg)

        assert len(await get_messages(channel_id=str(server_channel.id))) == 10

        item_pos = 4
        before_id = messages[item_pos].pk
        response = await authorized_client.get(
            f"channels/{str(server_channel.pk)}/messages?before={str(before_id)}&limit=3"
        )
        assert response.status_code == 200
        json_resp = response.json()
        assert len(json_resp) == 3

        for i, msg in enumerate(json_resp):
            item_pos -= 1
            prev_message = messages[item_pos]
            assert str(prev_message.pk) == msg["id"]

    @pytest.mark.asyncio
    async def test_get_messages_after_id(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
    ):
        messages = []
        for i in range(10):
            content = f"message {i}"
            msg = await create_item(
                item=MessageCreateSchema(server=str(server.id), channel=str(server_channel.id), content=content),
                result_obj=Message,
                current_user=current_user,
                user_field="author",
            )
            messages.append(msg)

        assert len(await get_messages(channel_id=str(server_channel.id))) == 10

        item_pos = 4
        before_id = messages[item_pos].pk
        response = await authorized_client.get(
            f"channels/{str(server_channel.pk)}/messages?after={str(before_id)}&limit=3"
        )
        assert response.status_code == 200
        json_resp = response.json()
        assert len(json_resp) == 3

        for i, msg in enumerate(json_resp):
            item_pos += 1
            prev_message = messages[item_pos]
            assert str(prev_message.pk) == msg["id"]

    @pytest.mark.asyncio
    async def test_get_messages_after_id_none(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
    ):
        messages = []
        for i in range(3):
            content = f"message {i}"
            msg = await create_item(
                item=MessageCreateSchema(server=str(server.id), channel=str(server_channel.id), content=content),
                result_obj=Message,
                current_user=current_user,
                user_field="author",
            )
            messages.append(msg)

        assert len(await get_messages(channel_id=str(server_channel.id))) == 3

        item_pos = 2
        before_id = messages[item_pos].pk
        response = await authorized_client.get(
            f"channels/{str(server_channel.pk)}/messages?after={str(before_id)}&limit=10"
        )
        assert response.status_code == 200
        json_resp = response.json()
        assert len(json_resp) == 0

    @pytest.mark.asyncio
    async def test_get_messages_before_id_none(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
    ):
        messages = []
        for i in range(3):
            content = f"message {i}"
            msg = await create_item(
                item=MessageCreateSchema(server=str(server.id), channel=str(server_channel.id), content=content),
                result_obj=Message,
                current_user=current_user,
                user_field="author",
            )
            messages.append(msg)

        assert len(await get_messages(channel_id=str(server_channel.id))) == 3

        item_pos = 0
        before_id = messages[item_pos].pk
        response = await authorized_client.get(
            f"channels/{str(server_channel.pk)}/messages?before={str(before_id)}&limit=3"
        )
        assert response.status_code == 200
        json_resp = response.json()
        assert len(json_resp) == 0

    @pytest.mark.asyncio
    async def test_get_messages_around_id_limit_pair(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
    ):
        messages = []
        for i in range(10):
            content = f"message {i}"
            msg = await create_item(
                item=MessageCreateSchema(server=str(server.id), channel=str(server_channel.id), content=content),
                result_obj=Message,
                current_user=current_user,
                user_field="author",
            )
            messages.append(msg)

        assert len(await get_messages(channel_id=str(server_channel.id))) == 10

        item_pos = 4
        limit = 5
        around_id = messages[item_pos].pk
        response = await authorized_client.get(
            f"channels/{str(server_channel.pk)}/messages?around={str(around_id)}&limit={limit}"
        )
        assert response.status_code == 200
        json_resp = response.json()
        assert len(json_resp) == 5

        before_count = limit // 2
        after_count = limit // 2

        expected_messages = [
            messages[item_pos - before_count],
            messages[item_pos - before_count + 1],
            messages[item_pos],
            messages[item_pos + after_count - 1],
            messages[item_pos + after_count],
        ]

        expected_message_ids = [str(message.pk) for message in expected_messages]
        result_message_ids = [message["id"] for message in json_resp]
        assert expected_message_ids[::-1] == result_message_ids

    @pytest.mark.asyncio
    async def test_get_messages_around_id_limit_even(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        server: Server,
        server_channel: Channel,
    ):
        messages = []
        for i in range(10):
            content = f"message {i}"
            msg = await create_item(
                item=MessageCreateSchema(server=str(server.id), channel=str(server_channel.id), content=content),
                result_obj=Message,
                current_user=current_user,
                user_field="author",
            )
            messages.append(msg)

        assert len(await get_messages(channel_id=str(server_channel.id))) == 10

        item_pos = 4
        limit = 4
        around_id = messages[item_pos].pk
        response = await authorized_client.get(
            f"channels/{str(server_channel.pk)}/messages?around={str(around_id)}&limit={limit}"
        )
        assert response.status_code == 200
        json_resp = response.json()
        assert len(json_resp) == 4

        before_count = limit // 2
        after_count = (limit // 2) - 1

        expected_messages = [
            messages[item_pos - before_count],
            messages[item_pos - before_count + 1],
            messages[item_pos],
            messages[item_pos + after_count],
        ]

        expected_message_ids = [str(message.pk) for message in expected_messages]
        result_message_ids = [message["id"] for message in json_resp]
        assert expected_message_ids[::-1] == result_message_ids

    @pytest.mark.asyncio
    async def test_get_messages_before_id_non_object_id(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server_channel: Channel
    ):
        before_id = "0"
        response = await authorized_client.get(f"channels/{str(server_channel.pk)}/messages?before={before_id}&limit=3")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_messages_after_id_non_object_id(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server_channel: Channel
    ):
        after_id = "0"
        response = await authorized_client.get(f"channels/{str(server_channel.pk)}/messages?after={after_id}&limit=3")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_message_as_app(
        self,
        app: FastAPI,
        db: Database,
        topic_channel: Channel,
        integration_app: App,
        get_app_authorized_client: Callable,
    ):
        data = {"content": "gm!", "channel": str(topic_channel.pk)}
        app_client = await get_app_authorized_client(integration_app, channels=[topic_channel])
        response = await app_client.post("/messages", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert "content" in json_response
        assert json_response["content"] == data["content"]
        assert json_response["channel"] == data["channel"] == str(topic_channel.pk)
        assert json_response["author"] is None
        assert json_response["app"] is not None
        assert json_response["app"] == str(integration_app.pk)
        assert json_response["type"] == 3

    @pytest.mark.asyncio
    async def test_create_empty_message_fails(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        topic_channel: Channel,
    ):
        data = {"blocks": [{"type": "paragraph", "children": [{"text": ""}]}], "channel": str(topic_channel.pk)}
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_post_report_message(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        create_new_user: Callable,
        get_authorized_client: Callable,
        topic_channel: Channel,
    ):
        guest_user = await create_new_user()

        authorized_client = await get_authorized_client(current_user)
        invite_data = {"members": [str(guest_user.pk)]}
        response = await authorized_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=invite_data)
        assert response.status_code == 204

        guest_client = await get_authorized_client(guest_user)
        data = {"content": "gm!", "channel": str(topic_channel.pk)}
        response = await guest_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json()["id"]

        data = {"reason": "spam"}
        authorized_client = await get_authorized_client(current_user)
        response = await authorized_client.post(f"/messages/{message_id}/report", json=data)
        assert response.status_code == 201
        json_resp = response.json()
        assert json_resp.get("author") == str(current_user.pk)
        assert json_resp.get("message") == message_id
        assert json_resp.get("reason") == "spam"

    @pytest.mark.asyncio
    async def test_post_report_own_message(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        authorized_client: AsyncClient,
        topic_channel: Channel,
    ):

        data = {"content": "gm!", "channel": str(topic_channel.pk)}
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json()["id"]

        data = {"reason": "spam"}
        response = await authorized_client.post(f"/messages/{message_id}/report", json=data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_post_create_message_as_non_whitelisted_guest(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        create_new_user: Callable,
        get_authorized_client: Callable,
        topic_channel: Channel,
        mock_whitelist_feature,
    ):
        guest_user = await create_new_user()

        authorized_client = await get_authorized_client(current_user)
        invite_data = {"members": [str(guest_user.pk)]}
        response = await authorized_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=invite_data)
        assert response.status_code == 204

        guest_client = await get_authorized_client(guest_user)
        data = {"content": "gm!", "channel": str(topic_channel.pk)}
        response = await guest_client.post("/messages", json=data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_post_create_message_as_whitelisted_guest(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        create_new_user: Callable,
        get_authorized_client: Callable,
        topic_channel: Channel,
        mock_whitelist_feature,
    ):
        guest_user = await create_new_user()

        authorized_client = await get_authorized_client(current_user)
        invite_data = {"members": [str(guest_user.pk)]}
        response = await authorized_client.post(f"/channels/{str(topic_channel.pk)}/invite", json=invite_data)
        assert response.status_code == 204

        guest_client = await get_authorized_client(guest_user)
        data = {"content": "gm!", "channel": str(topic_channel.pk)}
        response = await guest_client.post("/messages", json=data)
        assert response.status_code == 403

        await whitelist_wallet(wallet_address=guest_user.wallet_address)
        response = await guest_client.post("/messages", json=data)
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_answer_dm_non_whitelisted(
        self,
        app: FastAPI,
        db: Database,
        current_user: User,
        create_new_user: Callable,
        get_authorized_client: Callable,
        mock_whitelist_feature,
    ):
        await whitelist_wallet(current_user.wallet_address)

        guest_user = await create_new_user()

        authorized_client = await get_authorized_client(current_user)
        members = [current_user, guest_user]
        data = {"kind": "dm", "members": [str(member.pk) for member in members]}

        response = await authorized_client.post("/channels", json=data)
        assert response.status_code == 201
        dm_channel_id = response.json()["id"]

        guest_client = await get_authorized_client(guest_user)
        data = {"content": "gm!", "channel": dm_channel_id}
        response = await guest_client.post("/messages", json=data)
        assert response.status_code == 201
