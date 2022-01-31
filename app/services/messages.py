import asyncio
import http
from typing import List, Union

from fastapi import HTTPException

from app.models.base import APIDocument
from app.models.channel import Channel
from app.models.message import Message, MessageReaction
from app.models.user import User
from app.schemas.messages import MessageCreateSchema
from app.services.crud import create_item, delete_item, get_item_by_id, get_items
from app.services.websockets import (
    broadcast_delete_message,
    broadcast_new_message,
    broadcast_new_reaction,
    broadcast_remove_reaction,
)


async def create_message(message_model: MessageCreateSchema, current_user: User) -> Union[Message, APIDocument]:
    message = await create_item(item=message_model, result_obj=Message, current_user=current_user, user_field="author")
    asyncio.create_task(broadcast_new_message(str(message.id), str(current_user.id)))
    return message


async def delete_message(message_id: str, current_user: User):
    message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=current_user)
    if not message.author == current_user:
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN)

    asyncio.create_task(broadcast_delete_message(str(message.id), str(current_user.id)))

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
        asyncio.create_task(
            broadcast_new_reaction(message_id=message_id, reaction=reaction, author_id=str(current_user.id))
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
        asyncio.create_task(
            broadcast_remove_reaction(message_id=message_id, reaction=reaction, author_id=str(current_user.id))
        )

    return message
