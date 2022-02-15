import json
import logging

from app.models.user import User
from app.schemas.ws_events import CreateMarkChannelReadEvent
from app.services.channels import update_channels_read_state
from app.services.users import get_user_by_id
from app.services.websockets import broadcast_connection_ready

logger = logging.getLogger(__name__)


async def _get_user_from_event(event: dict) -> User:
    channel_name = event["channel"]
    user_id = channel_name.split("-")[1]
    user = await get_user_by_id(user_id)
    if not user:
        raise Exception(f"Missing user. [user_id={user_id}]")
    return user


async def handle_pusher_event(event: dict):
    event_name = event["name"]
    if event_name == "client_event":
        return await handle_pusher_client_event(event)

    channel_name = event["channel"]
    user = await _get_user_from_event(event)

    if event_name == "channel_occupied":
        await process_channel_occupied_event(channel_name=channel_name, current_user=user)
    elif event_name == "channel_vacated":
        await process_channel_vacated_event(channel_name=channel_name, current_user=user)
    else:
        raise NotImplementedError(f"not expected event: {event}")

    logger.info("pusher event handled successfully. [event=%s, channel=%s]", event_name, channel_name)


async def handle_pusher_client_event(event: dict):
    channel_name = event["channel"]
    user = await _get_user_from_event(event)

    client_event: str = event["event"]
    if client_event == "client-connection-request":
        await broadcast_connection_ready(current_user=user, channel=channel_name)
    elif client_event.startswith("client-channel-mark"):
        event_data = json.loads(event["data"])
        single_channel_id = event_data.pop("channel_id")
        if single_channel_id:
            event_data["channel_ids"] = [single_channel_id]
        event_model = CreateMarkChannelReadEvent(**event_data)
        await process_channel_mark_read_event(event_model=event_model, current_user=user)
    else:
        raise NotImplementedError(f"not expected client event: {event}")

    logger.info("client event handled successfully. [client_event=%s, channel=%s]", client_event, channel_name)


async def process_channel_occupied_event(channel_name: str, current_user: User):
    update_data = {"$addToSet": {"online_channels": channel_name}}
    await User.collection.update_one(filter={"_id": current_user.pk}, update=update_data)


async def process_channel_vacated_event(channel_name: str, current_user: User):
    update_data = {"$pull": {"online_channels": channel_name}}
    await User.collection.update_one(filter={"_id": current_user.pk}, update=update_data)


async def process_channel_mark_read_event(event_model: CreateMarkChannelReadEvent, current_user: User):
    await update_channels_read_state(
        channel_ids=event_model.channel_ids, last_read_at=event_model.last_read_at, current_user=current_user
    )
