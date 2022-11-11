import logging
from typing import List, Optional

from app.helpers.events import EventType, fetch_event_channel_scope
from app.helpers.list_utils import batch_list
from app.helpers.pusher import broadcast_pusher
from app.helpers.queue_utils import timed_task
from app.models.app import App, AppInstalled
from app.models.channel import Channel
from app.models.message import Message
from app.models.user import User
from app.services.crud import get_item_by_id, get_items

logger = logging.getLogger(__name__)


async def get_ws_online_channels(channel: Channel) -> List[str]:
    pusher_channels = []

    if not channel.members:
        return []

    all_user_ids = [member.pk for member in channel.members]
    async for batch_user_ids in batch_list(all_user_ids, chunk_size=100):
        users = await get_items(filters={"_id": {"$in": batch_user_ids}}, result_obj=User, limit=None)
        user: User
        for user in users:
            pusher_channels.extend(user.online_channels)

    installed_apps = await get_items(filters={"channel": channel.pk}, result_obj=AppInstalled, limit=None)
    async for batch_app_ids in batch_list(installed_apps, chunk_size=100):
        apps = await get_items(filters={"_id": {"$in": batch_app_ids}}, result_obj=App, limit=None)
        app: App
        for app in apps:
            pusher_channels.extend(app.online_channels)

    return pusher_channels


async def broadcast_server_event(
    server_id: str, current_user_id: str, event: EventType, custom_data: Optional[dict] = None
):
    raise NotImplementedError("servers not supported anymore")


async def fetch_ws_channels_for_scope(scope: str, event: EventType, data: dict) -> List[str]:
    if scope == "channel":
        channel_dict = data.get("channel")
        message_dict = data.get("message")
        message_id = data.get("message_id", "")

        if channel_dict:
            if isinstance(channel_dict, dict):
                channel_id = channel_dict.get("id")
            else:
                channel_id = channel_dict
        elif message_dict:
            if isinstance(message_dict, dict):
                channel_id = message_dict.get("channel")
            elif isinstance(message_dict, str):
                message = await get_item_by_id(id_=message_dict, result_obj=Message)
                channel_id = str(message.channel.pk)
            else:
                raise Exception("unexpected data", data)
        elif message_id:
            message = await get_item_by_id(id_=message_id, result_obj=Message)
            channel_id = str(message.channel.pk)
        else:
            raise Exception(f"expected 'channel' or 'message' in event {event}: {data}")

        channel = await get_item_by_id(id_=channel_id, result_obj=Channel)
        if not channel:
            raise Exception(f"channel not found: {channel_id}")

        websocket_channels = await get_ws_online_channels(channel)
    elif scope == "user":
        user_dict = data.get("user")
        if not user_dict:
            raise Exception("expected 'user' in event data: %s. [event=%s]", data, event.name)

        user_id = user_dict.get("id")
        user = await get_item_by_id(id_=user_id, result_obj=User)

        websocket_channels = user.online_channels
    elif scope == "user_channels":
        websocket_channels = []
        user_dict = data.get("user")
        if not user_dict:
            raise Exception("expected 'user' in event data: %s. [event=%s]", data, event.name)

        user_id = user_dict.get("id")
        user = await get_item_by_id(id_=user_id, result_obj=User)

        channels = await get_items(filters={"members": user.pk}, result_obj=Channel, limit=None)
        for channel in channels:
            websocket_channels.extend(await get_ws_online_channels(channel))
    else:
        raise Exception("unexpected scope: %s", scope)

    return websocket_channels


@timed_task()
async def broadcast_websocket_message(event: EventType, data: dict):
    event_scope = await fetch_event_channel_scope(event)
    logger.debug("scope: %s. [event=%s]", event_scope, event.name)

    if not event_scope:
        return

    websocket_channels = await fetch_ws_channels_for_scope(event_scope, event, data)
    logger.debug("# online websocket channels: %d. [event=%s]", len(websocket_channels), event.name)

    await broadcast_pusher(event, data=data, pusher_channels=websocket_channels)
