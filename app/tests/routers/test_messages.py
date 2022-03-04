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
from app.models.channel import Channel
from app.models.message import Message, MessageReaction
from app.models.server import Server
from app.models.user import User
from app.schemas.messages import MessageCreateSchema
from app.services.crud import create_item, get_item_by_id
from app.services.messages import get_messages


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
        messages = await get_messages(channel_id=str(server_channel.id), current_user=current_user, size=100)
        assert len(messages) == 1

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
        assert message == channel_message
        assert len(message.reactions) == 0

        response = await authorized_client.post(f"/messages/{str(message.id)}/reactions/🙌")
        assert response.status_code == 204

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
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

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
        assert message == channel_message
        assert len(message.reactions) == 1

        response = await authorized_client.post(f"/messages/{str(message.id)}/reactions/{emoji}")
        assert response.status_code == 204

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
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

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
        assert message == channel_message
        assert len(message.reactions) == 1

        response = await authorized_client.post(f"/messages/{str(message.id)}/reactions/{emoji}")
        assert response.status_code == 204

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
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

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
        assert message == channel_message
        assert len(message.reactions) == 1

        new_emoji = "💪"
        response = await authorized_client.post(f"/messages/{str(message.id)}/reactions/{new_emoji}")
        assert response.status_code == 204

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
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

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
        assert message == channel_message
        assert len(message.reactions) == 1

        response = await authorized_client.delete(f"/messages/{str(message.id)}/reactions/😍")
        assert response.status_code == 204

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
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

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
        assert message == channel_message
        assert len(message.reactions) == 1

        response = await authorized_client.delete(f"/messages/{str(message.id)}/reactions/😍")
        assert response.status_code == 204

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
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
        event_loop,
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

        await asyncio.sleep(random.random(), loop=event_loop)
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
        messages = await get_messages(channel_id=str(server_channel.id), current_user=current_user, size=10)
        assert len(messages) == 1

        response = await authorized_client.delete(f"/messages/{str(channel_message.id)}")
        assert response.status_code == 204

        messages = await get_messages(channel_id=str(server_channel.id), current_user=current_user, size=10)
        assert len(messages) == 0

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
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

        messages = await get_messages(channel_id=str(server_channel.id), current_user=current_user, size=10)
        assert len(messages) == 1

        guest_2_client = await get_authorized_client(guest_user_2)
        response = await guest_2_client.delete(f"/messages/{str(channel_message.id)}")
        assert response.status_code == 403

        messages = await get_messages(channel_id=str(server_channel.id), current_user=current_user, size=10)
        assert len(messages) == 1

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
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

        messages = await get_messages(channel_id=str(server_channel.id), current_user=current_user, size=10)
        assert len(messages) == 1

        response = await authorized_client.delete(f"/messages/{str(channel_message.id)}")
        assert response.status_code == 204

        messages = await get_messages(channel_id=str(server_channel.id), current_user=current_user, size=10)
        assert len(messages) == 0

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
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
        message = await get_item_by_id(
            id_=channel_message.id, result_obj=Message, current_user=current_user
        )  # type: Message
        assert message.edited_at is None

        data = {"content": "new message update!"}
        response = await authorized_client.patch(f"/messages/{str(channel_message.id)}", json=data)
        assert response.status_code == 200
        json_response = response.json()

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
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
            "content": f"hey @<u:{str(guest_user.id)}>, what up?",
            "server": str(server.id),
            "channel": str(server_channel.id),
        }
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=current_user)
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
            "content": f"hey @<u:{str(guest_user_1.id)}> and @<u:{str(guest_user_2.id)}>, what up?",
            "server": str(server.id),
            "channel": str(server_channel.id),
        }
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=current_user)
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
            "content": f"hey @<u:{str(guest_user.id)}> and @<x:{str(ObjectId())}>, what up?",
            "server": str(server.id),
            "channel": str(server_channel.id),
        }
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=current_user)
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
            "content": f"hey @<b:here>, what up?",
            "server": str(server.id),
            "channel": str(server_channel.id),
        }
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=current_user)
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
            "content": f"hey @<b:here> and @<u:{str(guest_user.id)}>, what up?",
            "server": str(server.id),
            "channel": str(server_channel.id),
        }
        response = await authorized_client.post("/messages", json=data)
        assert response.status_code == 201
        message_id = response.json().get("id")
        message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=current_user)
        mentions = await get_message_mentions(message)
        assert len(mentions) == 2
        mention_type, mention_ref = mentions[0]
        assert mention_type == "user"
        assert mention_ref == str(guest_user.id)
        mention_type, mention_ref = mentions[1]
        assert mention_type == "broadcast"
        assert mention_ref == "here"

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
        message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=current_user)
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
        message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=current_user)
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
        message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=current_user)
        mentions = await get_message_mentions(message)
        assert len(mentions) == 1
        mention_type, mention_ref = mentions[0]
        assert mention_type == "user"
        assert mention_ref == str(guest_user.id)

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
        message = await get_item_by_id(
            id_=channel_message.id, result_obj=Message, current_user=current_user
        )  # type: Message
        assert message.edited_at is None

        content = "new message update!"
        blocks = await blockify_content(content)
        data = {"blocks": blocks}
        response = await authorized_client.patch(f"/messages/{str(channel_message.id)}", json=data)
        assert response.status_code == 200
        json_response = response.json()

        message = await get_item_by_id(id_=channel_message.id, result_obj=Message, current_user=current_user)
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
        message = await get_item_by_id(
            id_=channel_message.id, result_obj=Message, current_user=current_user
        )  # type: Message
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
        message = await get_item_by_id(
            id_=channel_message.id, result_obj=Message, current_user=current_user
        )  # type: Message
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
        messages = await get_messages(channel_id=str(server_channel.id), current_user=current_user, size=10)
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

        messages = await get_messages(channel_id=str(server_channel.id), current_user=current_user, size=10)
        assert len(messages) == 2
