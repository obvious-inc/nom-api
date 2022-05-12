import http
import logging
from datetime import datetime, timezone
from typing import List, Union
from urllib.parse import urlparse

from bson import ObjectId
from fastapi import HTTPException

from app.helpers.channels import fetch_channel_data, get_channel_online_users, get_channel_users, is_user_in_channel
from app.helpers.message_utils import blockify_content, get_message_mentions, stringify_blocks
from app.helpers.permissions import Permission, needs
from app.helpers.queue_utils import queue_bg_task, queue_bg_tasks
from app.helpers.ws_events import WebSocketServerEvent
from app.models.base import APIDocument
from app.models.channel import ChannelReadState
from app.models.message import Message, MessageReaction
from app.models.user import User
from app.schemas.channels import ChannelReadStateCreateSchema
from app.schemas.messages import MessageCreateSchema, MessageUpdateSchema
from app.services.channels import update_channel_last_message
from app.services.crud import (
    create_item,
    delete_item,
    find_and_update_item,
    get_item,
    get_item_by_id,
    get_items,
    update_item,
)
from app.services.integrations import get_gif_by_url
from app.services.users import get_user_by_id
from app.services.websockets import broadcast_current_user_event, broadcast_message_event, broadcast_users_event

logger = logging.getLogger(__name__)


@needs(permissions=[Permission.MESSAGES_CREATE])
async def create_message(message_model: MessageCreateSchema, current_user: User) -> Union[Message, APIDocument]:
    if message_model.blocks and not message_model.content:
        message_model.content = await stringify_blocks(message_model.blocks)
    elif message_model.content and not message_model.blocks:
        message_model.blocks = await blockify_content(message_model.content)
    else:
        pass

    message = await create_item(item=message_model, result_obj=Message, current_user=current_user, user_field="author")

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
        (process_message_mentions, (str(message.id), str(current_user.id))),
    ]

    # mypy has some issues with changing Callable signatures so we have to exclude that type check:
    # https://github.com/python/mypy/issues/10740
    await queue_bg_tasks(bg_tasks)  # type: ignore[arg-type]

    return message


async def update_message(message_id: str, update_data: MessageUpdateSchema, current_user: User):
    message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=current_user)
    if not message.author == current_user:
        raise HTTPException(status_code=http.HTTPStatus.FORBIDDEN)

    if update_data.blocks and not update_data.content:
        update_data.content = await stringify_blocks(update_data.blocks)
    elif update_data.content and not update_data.blocks:
        update_data.blocks = await blockify_content(update_data.content)
    else:
        pass

    data = update_data.dict()
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


@needs(permissions=[Permission.MESSAGES_LIST])
async def get_messages(channel_id: str, current_user: User, **common_params) -> List[Message]:
    channel = await fetch_channel_data(channel_id=channel_id)
    if not channel:
        raise Exception(f"couldn't find channel information for channel with id: {channel_id}")

    filters = {"channel": ObjectId(channel_id)}
    if channel.get("kind") == "server":
        filters["server"] = ObjectId(channel.get("server"))

    around_id = common_params.pop("around", None)
    if around_id:
        return await _get_around_messages(
            around_message_id=around_id, filters=filters, current_user=current_user, **common_params
        )

    messages = await get_items(filters=filters, result_obj=Message, current_user=current_user, **common_params)
    return messages


async def _get_around_messages(
    around_message_id: str, filters: dict, current_user: User, **common_params
) -> List[Message]:
    around_message = await get_item_by_id(id_=around_message_id, result_obj=Message, current_user=current_user)

    limit = common_params.get("limit", 50)
    before_count = limit // 2
    after_count = limit // 2
    if limit % 2 == 0:
        after_count -= 1

    before_params = {**common_params, "limit": before_count, "before": around_message_id}
    before_messages = await get_items(filters=filters, result_obj=Message, current_user=current_user, **before_params)

    after_params = {**common_params, "limit": after_count, "after": around_message_id}
    after_messages = await get_items(filters=filters, result_obj=Message, current_user=current_user, **after_params)

    messages = after_messages[::-1] + [around_message] + before_messages
    return messages


@needs(permissions=[Permission.MESSAGES_LIST])
async def get_message(channel_id: str, message_id: str, current_user: User) -> Message:
    filters = {"_id": ObjectId(message_id), "channel": ObjectId(channel_id)}
    return await get_item(filters=filters, result_obj=Message, current_user=current_user)


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


async def process_message_mentions(message_id: str, user_id: str):
    current_user = await get_user_by_id(user_id=user_id)
    message = await get_item_by_id(id_=message_id, result_obj=Message, current_user=current_user)
    channel = await message.channel.fetch()
    mentions = await get_message_mentions(message)
    if not mentions:
        return

    users_to_notify = []

    for mention_type, mention_ref in mentions:
        logger.debug(f"should send notification of type '{mention_type}' to @{mention_ref}")

        if mention_type == "user":
            user_id = mention_ref
            user = await get_user_by_id(user_id)
            users_to_notify.append(user)

        if mention_type == "broadcast":
            if mention_ref == "here":
                online_users = await get_channel_online_users(channel=channel)
                users_to_notify.extend(online_users)
            elif mention_ref == "channel" or mention_ref == "everyone":
                channel_users = await get_channel_users(channel=channel)
                users_to_notify.extend(channel_users)
            else:
                logger.warning(f"unknown mention reference: {mention_ref}")
                continue

    if len(users_to_notify) == 0:
        logger.debug("no users to notify")
        return

    for user in users_to_notify:
        user_in_channel = await is_user_in_channel(user=user, channel=channel)
        if not user_in_channel:
            continue

        read_state = await find_and_update_item(
            filters={"user": user.pk, "channel": channel.pk},
            data={"$inc": {"mention_count": 1}},
            result_obj=ChannelReadState,
        )

        if not read_state:
            read_state_model = ChannelReadStateCreateSchema(
                channel=str(channel.id),
                last_read_at=datetime.fromtimestamp(0, tz=timezone.utc),
                mention_count=1,
            )
            await create_item(read_state_model, result_obj=ChannelReadState, current_user=user)

        # TODO: Create mention activity entry

    await broadcast_users_event(
        users=users_to_notify,
        event=WebSocketServerEvent.NOTIFY_USER_MENTION,
        custom_data={"message": message.dump()},
    )

    # TODO: Broadcast push notifications
    offline_users = [user for user in users_to_notify if not user.status or user.status == "offline"]
    if offline_users:
        logger.debug(f"TBD | sending push notifications to {len(offline_users)} offline users")


async def create_reply_message(
    reply_to_message_id: str,
    message_model: MessageCreateSchema,
    current_user: User,
) -> Union[Message, APIDocument]:
    message_model.reply_to = reply_to_message_id
    reply = await create_message(message_model=message_model, current_user=current_user)
    return reply
