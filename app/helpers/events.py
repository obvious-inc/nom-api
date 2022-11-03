import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    MESSAGE_CREATE = "MESSAGE_CREATE"
    MESSAGE_REMOVE = "MESSAGE_REMOVE"
    MESSAGE_UPDATE = "MESSAGE_UPDATE"
    MESSAGE_REACTION_ADD = "MESSAGE_REACTION_ADD"
    MESSAGE_REACTION_REMOVE = "MESSAGE_REACTION_REMOVE"

    CHANNEL_READ = "CHANNEL_READ"
    CHANNEL_UPDATE = "CHANNEL_UPDATE"
    CHANNEL_USER_INVITED = "CHANNEL_USER_INVITED"
    CHANNEL_USER_JOINED = "CHANNEL_USER_JOINED"
    CHANNEL_DELETED = "CHANNEL_DELETED"

    USER_PROFILE_UPDATE = "USER_PROFILE_UPDATE"
    USER_PRESENCE_UPDATE = "USER_PRESENCE_UPDATE"
    USER_TYPING = "USER_TYPING"

    # DEPRECATED Server events
    SERVER_PROFILE_UPDATE = "SERVER_PROFILE_UPDATE"
    SERVER_USER_JOINED = "SERVER_USER_JOINED"
    SERVER_UPDATE = "SERVER_UPDATE"

    SERVER_SECTION_CREATE = "SERVER_SECTION_CREATE"
    SERVER_SECTION_UPDATE = "SERVER_SECTION_UPDATE"
    SERVER_SECTION_DELETE = "SERVER_SECTION_DELETE"
    SERVER_SECTIONS_UPDATE = "SERVER_SECTIONS_UPDATE"

    NOTIFY_USER_MENTION = "NOTIFY_USER_MENTION"


async def fetch_event_channel_scope(event: EventType) -> Optional[str]:
    if event in [
        EventType.MESSAGE_CREATE,
        EventType.MESSAGE_REMOVE,
        EventType.MESSAGE_UPDATE,
        EventType.MESSAGE_REACTION_ADD,
        EventType.MESSAGE_REACTION_REMOVE,
        EventType.CHANNEL_UPDATE,
        EventType.CHANNEL_USER_INVITED,
        EventType.CHANNEL_USER_JOINED,
        EventType.CHANNEL_DELETED,
        EventType.USER_TYPING,
    ]:
        return "channel"
    elif event in [EventType.CHANNEL_READ]:
        return "user"
    elif event in [EventType.USER_PROFILE_UPDATE, EventType.USER_PRESENCE_UPDATE]:
        return "user_channels"
    else:
        logger.warning(f"unexpected event: {event}")
        return None
