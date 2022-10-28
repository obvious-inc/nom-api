from typing import Optional

from app.helpers.events import EventType
from app.helpers.message_utils import get_raw_blocks
from app.helpers.push_notifications import broadcast_push_event
from app.models.message import Message
from app.models.user import User
from app.services.crud import get_item_by_id, get_items
from app.services.websockets import broadcast_ws_event


async def _batch_channel_members(channel_members, chunk_size=90):
    total_length = len(channel_members)
    for ndx in range(0, total_length, chunk_size):
        yield channel_members[ndx : min(ndx + chunk_size, total_length)]


async def broadcast_message_notifications(
    message_id: str, current_user_id: Optional[str], event: EventType, custom_data: Optional[dict] = None
):
    message = await get_item_by_id(id_=message_id, result_obj=Message)
    # todo: improve this to somehow avoid the fetch
    channel = await message.channel.fetch()
    if not channel:
        raise Exception("expected message to have a channel")

    author: User = await message.author.fetch()

    # todo: create a separate schema for WS events data
    dumped_message = await message.to_dict()

    ws_data = {"message": dumped_message}
    if custom_data:
        ws_data.update(custom_data)

    push_title = f"{author.display_name or author.wallet_address} (#{channel.name})"
    push_body = (await get_raw_blocks(message.blocks))[:100]

    push_data = {
        "title": push_title,
        "body": push_body,
        "metadata": dumped_message,
    }

    async for batch_members in _batch_channel_members(channel.members):
        await broadcast_message_to_channel_members(
            channel_members=batch_members, event=event, ws_data=ws_data, push_data=push_data
        )


async def broadcast_message_to_channel_members(channel_members, event: EventType, ws_data: dict, push_data: dict):
    channel_members_pks = [member.pk for member in channel_members]
    listening_users = await get_items(filters={"_id": {"$in": channel_members_pks}}, result_obj=User, limit=None)

    ws_online_channels = set()
    push_offline_tokens = set()

    for user in listening_users:
        if user.online_channels:
            ws_online_channels.update(user.online_channels)
        else:
            push_offline_tokens.update(user.push_tokens)

    await broadcast_ws_event(event, data=ws_data, ws_channels=list(ws_online_channels))
    if event == EventType.MESSAGE_CREATE:
        await broadcast_push_event(event, data=push_data, push_tokens=list(push_offline_tokens))
