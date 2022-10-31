import logging
from datetime import datetime, timezone
from typing import List

from umongo import Reference

from app.helpers.channels import is_user_in_channel
from app.helpers.events import EventType
from app.helpers.message_utils import get_message_mentions, get_raw_blocks
from app.helpers.push_notifications import broadcast_push_event
from app.models.channel import ChannelReadState
from app.models.message import Message
from app.models.user import User
from app.schemas.channels import ChannelReadStateCreateSchema
from app.services.crud import create_item, find_and_update_item, get_item_by_id
from app.services.users import get_user_by_id
from app.services.websockets import broadcast_websocket_event

logger = logging.getLogger(__name__)


async def _batch_user_ids(user_ids: List[Reference], chunk_size: int = 90):
    total_length = len(user_ids)
    for ndx in range(0, total_length, chunk_size):
        yield user_ids[ndx : min(ndx + chunk_size, total_length)]


async def _batch_list(list_: List, chunk_size: int = 90):
    total_length = len(list_)
    for ndx in range(0, total_length, chunk_size):
        yield list_[ndx : min(ndx + chunk_size, total_length)]


async def prepare_event_ws_data(event: EventType, data: dict) -> dict:
    # validate event data
    return data


async def prepare_event_push_data(event: EventType, data: dict) -> dict:
    pass


async def dispatch_websocket_event(event: EventType, data: dict):
    ws_data = await prepare_event_ws_data(event, data)

    # todo: for channel events and others, this needs to be changed
    message_dict = ws_data.get("message", {})
    message_id = message_dict.get("id")

    message = await get_item_by_id(id_=message_id, result_obj=Message)
    channel = await message.channel.fetch()
    if not channel:
        raise Exception("expected message to have a channel")

    all_user_ids = [member.pk for member in channel.members]

    async for batch_user_ids in _batch_user_ids(all_user_ids):
        await broadcast_websocket_event(user_ids=batch_user_ids, ws_data=ws_data, event=event)


async def broadcast_push_notification(event: EventType, data: dict):
    message_dict = data.get("message", {})
    app_dict = data.get("app", {})
    message_id = message_dict.get("id")
    message = await get_item_by_id(id_=message_id, result_obj=Message)
    channel = await message.channel.fetch()
    if not channel:
        raise Exception("expected message to have a channel")

    if message.author:
        author: User = await message.author.fetch()
        author_name = author.display_name or author.wallet_address
    elif app_dict:
        author_name = app_dict.get("name")
    else:
        author_name = "New message"

    push_title = f"{author_name} (#{channel.name})"
    push_body = (await get_raw_blocks(message.blocks))[:100]
    push_metadata = {**data, "event": event.name}
    push_data = {"title": push_title, "body": push_body, "metadata": push_metadata}

    users_to_notify = []
    mentions = await get_message_mentions(message)
    for mention_type, mention_ref in mentions:
        logger.debug(f"should send notification of type '{mention_type}' to @{mention_ref}")

        if mention_type == "user":
            user_id = mention_ref
            user = await get_user_by_id(user_id)
            users_to_notify.append(user)

    if len(users_to_notify) == 0:
        logger.debug("no users to notify")
        return

    push_messages = []

    for user in users_to_notify:
        user_in_channel = await is_user_in_channel(user=user, channel=channel)
        if not user_in_channel:
            continue

        read_state = await find_and_update_item(
            filters={"user": user.pk, "channel": channel.pk},
            data={"$inc": {"mention_count": 1}},
            result_obj=ChannelReadState,
        )

        if read_state:
            mention_count = read_state.mention_count
        else:
            mention_count = 1
            read_state_model = ChannelReadStateCreateSchema(
                channel=str(channel.id),
                last_read_at=datetime.fromtimestamp(0, tz=timezone.utc),
                mention_count=mention_count,
            )
            await create_item(read_state_model, result_obj=ChannelReadState, current_user=user)

        if user.push_tokens and len(user.push_tokens) > 0:
            push_messages.append({**push_data, "to": user.push_tokens, "badge": mention_count})

    async for batched_messages in _batch_list(push_messages):
        await broadcast_push_event(push_messages=batched_messages)


async def broadcast_event(event: EventType, data: dict):
    logger.info(f"broadcasting new event: {event}")
    logger.debug(f"event data: {data}")

    await dispatch_websocket_event(event, data)
    if event == EventType.MESSAGE_CREATE:
        await broadcast_push_notification(event, data)
