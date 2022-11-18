import json
import logging
from typing import Optional, Union

from app.helpers.events import EventType
from app.helpers.queue_utils import queue_bg_task
from app.models.app import App
from app.models.user import User
from app.schemas.ws_events import CreateMarkChannelReadEvent
from app.services.channels import update_channels_read_state
from app.services.crud import get_item_by_id, update_item
from app.services.events import broadcast_event
from app.services.users import get_user_by_id

logger = logging.getLogger(__name__)


async def _get_user_from_event(event: dict) -> User:
    channel_name = event["channel"]
    user_id = channel_name.split("-")[1]
    user = await get_user_by_id(user_id)
    if not user:
        raise Exception(f"Missing user. [user_id={user_id}]")
    return user


async def _get_actor_from_event(event: dict) -> Optional[Union[User, App]]:
    channel_name = event["channel"]
    actor_id = channel_name.split("-")[1]
    user = await get_user_by_id(actor_id)
    if user:
        return user

    app = await get_item_by_id(id_=actor_id, result_obj=App)
    if app:
        return app

    return None


async def handle_pusher_event(event: dict):
    event_name = event["name"]
    if event_name == "client_event":
        return await handle_pusher_client_event(event)

    channel_name = event["channel"]
    actor = await _get_actor_from_event(event)

    if not actor:
        raise Exception(f"Missing actor. [channel_name={channel_name}]")

    if event_name == "channel_occupied":
        await process_channel_occupied_event(channel_name=channel_name, actor=actor)
    elif event_name == "channel_vacated":
        await process_channel_vacated_event(channel_name=channel_name, actor=actor)
    else:
        raise NotImplementedError(f"not expected event: {event}")

    logger.info("pusher event handled successfully. [event=%s, channel=%s]", event_name, channel_name)


async def handle_pusher_client_event(event: dict):
    channel_name = event["channel"]
    user = await _get_user_from_event(event)

    client_event: str = event["event"]
    if client_event.startswith("client-channel-mark"):
        event_data = json.loads(event["data"])
        single_channel_id = event_data.pop("channel_id")
        if single_channel_id:
            event_data["channel_ids"] = [single_channel_id]
        event_model = CreateMarkChannelReadEvent(**event_data)
        await process_channel_mark_read_event(event_model=event_model, current_user=user)
    else:
        raise NotImplementedError(f"not expected client event: {event}")

    logger.info("client event handled successfully. [client_event=%s, channel=%s]", client_event, channel_name)


async def process_channel_occupied_event(channel_name: str, actor: Union[User, App]):
    update_data = {"$addToSet": {"online_channels": channel_name}, "$set": {"status": "online"}}
    await actor.__class__.collection.update_one(filter={"_id": actor.pk}, update=update_data)
    if isinstance(actor, User):
        await queue_bg_task(
            broadcast_event,
            EventType.USER_PRESENCE_UPDATE,
            {"status": "online", "user": actor.dump()},
        )


async def process_channel_vacated_event(channel_name: str, actor: Union[User, App]):
    update_data = {"$pull": {"online_channels": channel_name}}
    await actor.__class__.collection.update_one(filter={"_id": actor.pk}, update=update_data)
    await actor.reload()
    if len(actor.online_channels) == 0:
        await update_item(item=actor, data={"status": "offline"})
        if isinstance(actor, User):
            await queue_bg_task(
                broadcast_event,
                EventType.USER_PRESENCE_UPDATE,
                {"status": "offline", "user": actor.dump()},
            )


async def process_channel_mark_read_event(event_model: CreateMarkChannelReadEvent, current_user: User):
    await update_channels_read_state(
        channel_ids=event_model.channel_ids, last_read_at=event_model.last_read_at, current_user=current_user
    )
