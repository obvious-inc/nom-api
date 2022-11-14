import logging

from app.helpers.events import EventType
from app.services.push_notifications import dispatch_push_notification_event
from app.services.websockets import broadcast_websocket_message

logger = logging.getLogger(__name__)


async def broadcast_event(event: EventType, data: dict):
    logger.info(f"broadcasting new event: {event}")

    # future event pipeline dispatching will be here
    await broadcast_websocket_message(event, data)
    await dispatch_push_notification_event(event, data)
