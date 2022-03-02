import http
from datetime import datetime, timezone
from typing import List, Union
from urllib.parse import urlparse

from fastapi import HTTPException

from app.helpers.message_utils import blockify_content, get_message_content_mentions, stringify_blocks
from app.helpers.queue_utils import queue_bg_task, queue_bg_tasks
from app.helpers.ws_events import WebSocketServerEvent
from app.models.base import APIDocument
from app.models.channel import Channel
from app.models.message import Message, MessageReaction
from app.models.user import User
from app.schemas.messages import MessageCreateSchema, MessageUpdateSchema
from app.services.channels import update_channel_last_message
from app.services.crud import create_item, delete_item, get_item_by_id, get_items, update_item
from app.services.integrations import get_gif_by_url
from app.services.users import get_user_by_id
from app.services.websockets import broadcast_current_user_event, broadcast_message_event


async def create_message(message_model: MessageCreateSchema, current_user: User) -> Union[Message, APIDocument]:
    if message_model.blocks and not message_model.content:
        message_model.content = await stringify_blocks(message_model.blocks)
    elif message_model.content and not message_model.blocks:
        message_model.blocks = await blockify_content(message_model.content)
    else:
        pass

    message = await create_item(item=message_model, result_obj=Message, current_user=current_user, user_field="author")
    mentions = await get_message_content_mentions(message.content)
    if mentions:
        mentions_obj = [{"type": mention_type, "id": mention_id} for mention_type, mention_id in mentions]
        data = {"mentions": mentions_obj}
        message = await update_item(item=message, data=data)

        # TODO: broadcast notifications...

    bg_tasks = [
        (broadcast_message_event, (str(message.id), str(current_user.id), WebSocketServerEvent.MESSAGE_CREATE)),
        (update_channel_last_message, (message.channel, message, current_user)),
        (
            broadcast_current_user_event,
            (
                str(current_user.id),
                WebSocketServerEvent.CHANNEL_READ,
                {"channel": (await message.channel.fetch()).dump(), "read_at": message.created_at.isoformat()},
            ),
        ),
        (post_process_message_creation, (str(message.id), str(current_user.id))),
    ]

    # mypy has some issues with changing Callable signatures so we have to exclude that type check:
    # https://github.com/python/mypy/issues/10740
    await queue_bg_tasks(bg_tasks)  # type: ignore[arg-type]

    return message


async def update_message(message_id: str, update_data: MessageUpdateSchema, current_user: User):
    message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=current_user)
    if not message.author == current_user:
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN)

    data = update_data.dict()

    if update_data.blocks and not update_data.content:
        update_data.content = await stringify_blocks(update_data.blocks)
    elif update_data.content and not update_data.blocks:
        update_data.blocks = await blockify_content(update_data.content)
    else:
        pass

    changed_content = any([update_data.content, update_data.blocks])
    if changed_content:
        data.update({"edited_at": datetime.now(timezone.utc)})

    updated_item = await update_item(item=message, data=data)

    await queue_bg_task(
        broadcast_message_event, str(message.id), str(current_user.id), WebSocketServerEvent.MESSAGE_UPDATE
    )

    return updated_item


async def delete_message(message_id: str, current_user: User):
    message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=current_user)
    can_delete = message.author == current_user

    if message.server:
        server = await message.server.fetch()
        can_delete |= server.owner == current_user

    if not can_delete:
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN)

    await queue_bg_task(
        broadcast_message_event, str(message.id), str(current_user.id), WebSocketServerEvent.MESSAGE_REMOVE
    )

    await delete_item(item=message)


async def get_messages(channel_id: str, size: int, current_user: User) -> List[Message]:
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel, current_user=current_user)

    filters = {}
    if channel.kind == "server":
        # TODO: make sure user can list channel's messages (in server + proper permissions)
        filters = {"channel": channel.id, "server": channel.server.pk}
    elif channel.kind == "dm":
        if current_user not in channel.members:
            raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN)
        filters = {"channel": channel.id}

    messages = await get_items(
        filters=filters,
        result_obj=Message,
        current_user=current_user,
        size=size,
    )

    return messages


async def add_reaction_to_message(message_id, reaction_emoji: str, current_user: User):
    message = await get_item_by_id(
        id_=message_id, result_obj=Message, current_user=current_user
    )  # type: Union[Message, APIDocument]

    reaction = MessageReaction(emoji=reaction_emoji, count=1, users=[current_user])
    existing_reactions = message.reactions

    found = False
    added = False
    for existing_reaction in existing_reactions:  # type: MessageReaction
        if existing_reaction.emoji == reaction.emoji:
            found = True
            if current_user in existing_reaction.users:
                break
            existing_reaction.count += 1
            existing_reaction.users.append(current_user.pk)
            added = True
            break

    if not found:
        existing_reactions.append(reaction)
        added = True

    if added:
        await message.commit()
        await queue_bg_task(
            broadcast_message_event,
            str(message.id),
            str(current_user.id),
            WebSocketServerEvent.MESSAGE_REACTION_ADD,
            {"reaction": reaction.dump(), "user": str(current_user.id)},
        )

    return message


async def remove_reaction_from_message(message_id, reaction_emoji: str, current_user: User):
    message = await get_item_by_id(
        id_=message_id, result_obj=Message, current_user=current_user
    )  # type: Union[Message, APIDocument]

    reaction = MessageReaction(emoji=reaction_emoji)

    existing_reactions = message.reactions

    remove_index = None
    removed = False
    for index, existing_reaction in enumerate(existing_reactions):  # type: (int, MessageReaction)
        if existing_reaction.emoji == reaction.emoji:
            if current_user not in existing_reaction.users:
                break

            if existing_reaction.count > 1:
                existing_reaction.count -= 1
                existing_reaction.users.remove(current_user)
                removed = True
            else:
                remove_index = index
            break

    if remove_index is not None:
        removed = True
        del existing_reactions[remove_index]

    if removed:
        await message.commit()
        await queue_bg_task(
            broadcast_message_event,
            str(message.id),
            str(current_user.id),
            WebSocketServerEvent.MESSAGE_REACTION_REMOVE,
            {"reaction": reaction.dump(), "user": str(current_user.id)},
        )

    return message


async def post_process_message_creation(message_id: str, user_id: str):
    user = await get_user_by_id(user_id=user_id)
    message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=user)
    data = {}

    # If a gif, embed it
    try:
        parsed_url = urlparse(message.content)
        if parsed_url.hostname and any([provider in parsed_url.hostname for provider in ["giphy", "tenor"]]):
            gif = await get_gif_by_url(gif_url=message.content)
            data["embeds"] = [gif]
    except Exception as e:
        raise e

    if not data:
        return

    await update_item(item=message, data=data, current_user=user)
