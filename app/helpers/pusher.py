import logging
import os
from typing import List, Optional

import pusher
from dotenv import load_dotenv
from pusher.aiohttp import AsyncIOBackend
from sentry_sdk import capture_exception

from app.helpers.events import EventType
from app.helpers.list_utils import batch_list

logger = logging.getLogger(__name__)

load_dotenv()

# https://pusher.com/docs/channels/server_api/http-api/#publishing-events
PUSHER_EVENT_MAX_CHANNELS = 100

# TODO: this kind of breaks away from FastAPI's default way of initializing 3rd party clients using dependencies,
#  but I couldn't find a straightforward way to initialize this once, and not per request. The startup events felt
#  more hacky than anything else, but might be worth another look.
pusher_client = pusher.Pusher(
    app_id=os.getenv("PUSHER_APP_ID"),
    key=os.getenv("PUSHER_KEY"),
    secret=os.getenv("PUSHER_SECRET"),
    cluster=os.getenv("PUSHER_CLUSTER", "eu"),
    backend=AsyncIOBackend,
    ssl=True,
)


async def broadcast_pusher(event: EventType, data: dict, pusher_channels: Optional[List[str]] = None):
    if not pusher_channels:
        logger.debug("no online websocket channels. [event=%s]", event)
        return

    has_errors = False
    event_name = event.value

    pusher_channels = list(set(pusher_channels))

    async for batch_pusher_channels in batch_list(pusher_channels, chunk_size=PUSHER_EVENT_MAX_CHANNELS):
        try:
            await pusher_client.trigger(channels=batch_pusher_channels, event_name=event_name, data=data)
        except Exception as e:
            logger.exception("Problem broadcasting event to Pusher channel. [event_name=%s]", event_name)
            capture_exception(e)
            has_errors = True

    if not has_errors:
        logger.info("Event broadcast successful. [event_name=%s]", event_name)
