import logging
from typing import List

from app.helpers.events import EventType
from app.helpers.expo import send_expo_push_notifications
from app.helpers.list_utils import batch_list
from app.helpers.message_utils import get_message_mentioned_users, get_raw_blocks
from app.models.channel import Channel, ChannelReadState
from app.models.message import Message
from app.models.user import User, UserPreferences
from app.services.crud import get_item, get_item_by_id, get_items

logger = logging.getLogger(__name__)


async def parse_push_notification_data(event_data: dict, message: Message, channel: Channel):
    app_dict = event_data.get("app", {})

    if message.author:
        author: User = await message.author.fetch()
        author_name = author.display_name or author.wallet_address
    elif app_dict:
        author_name = app_dict.get("name")
    else:
        author_name = "New message"

    push_title = f"{author_name} (#{channel.name})"
    push_body = (await get_raw_blocks(message.blocks))[:100]
    return {"title": push_title, "body": push_body}


async def should_send_push_notification(
    user: User, channel: Channel, mentioned_users: List[User], message: Message
) -> bool:
    # apply all fancy logic to decide on sending push notification
    # - is channel muted?
    # - is user mentioned?
    # - etc.

    if message.author == user:
        return False

    if message.type == 1:
        # ignore system messages like changing channel name or topic; or new members
        return False

    user_prefs = await get_item(filters={"user": user}, result_obj=UserPreferences)
    if user_prefs:
        channels = user_prefs.channels
        channel_prefs = channels.get(str(channel.pk), {})
        muted = channel_prefs.get("muted", False)
        mentions = channel_prefs.get("mentions", False)
        if muted is True:
            return False

        if mentions:
            return user in mentioned_users

    return True


async def dispatch_push_notification_event(event: EventType, data: dict):
    if event != EventType.MESSAGE_CREATE:
        return

    message_dict = data.get("message", {})
    message = await get_item_by_id(id_=message_dict.get("id"), result_obj=Message)
    channel = await message.channel.fetch()
    if not channel:
        raise Exception("expected a channel")

    if not channel.members:
        return

    message_push_data = await parse_push_notification_data(event_data=data, message=message, channel=channel)
    notification_data = {
        "event_name": event.name,
        "event_data": data,
        "url": f"channels/{str(channel.pk)}",
        "sound": "default",
        **message_push_data,
    }

    channel_user_ids = [member.pk for member in channel.members]
    mentioned_users = await get_message_mentioned_users(message=message)

    push_messages = []
    async for batch_user_ids in batch_list(channel_user_ids):
        users = await get_items(filters={"_id": {"$in": batch_user_ids}}, result_obj=User, limit=None)
        user: User
        for user in users:
            # validate notification logic for each (channel muted, mentioned, etc.)
            if await should_send_push_notification(
                user=user, channel=channel, mentioned_users=mentioned_users, message=message
            ):
                curr_read_state = await get_item(
                    filters={"user": user.pk, "channel": channel.pk},
                    result_obj=ChannelReadState,
                )
                mention_count = curr_read_state.mention_count if curr_read_state else 1

                if user.push_tokens and len(user.push_tokens) > 0:
                    push_messages.append({**notification_data, "to": user.push_tokens, "badge": mention_count})

    async for batched_messages in batch_list(push_messages):
        await send_expo_push_notifications(push_messages=batched_messages)
