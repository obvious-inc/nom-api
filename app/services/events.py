import logging

from app.helpers.events import EventType
from app.services.notifications import broadcast_message_notifications

logger = logging.getLogger(__name__)


async def broadcast_event(event: EventType, data: dict):
    logger.info(f"broadcasting new event: {event}")
    logger.debug(f"event data: {data}")

    # abstract this better via event name: event_name => specific processor/pipeline
    if event.name.startswith("MESSAGE_"):

        # validate data matches expected event data, e.g. event.validate_data()
        if "message" not in data:
            raise Exception(f"missing 'message_id' in event data: {data}")

        message_dict = data.get("message", {})

        if event == EventType.MESSAGE_CREATE:
            message_id = message_dict.get("id")
            await broadcast_message_notifications(message_id, None, event, None)
