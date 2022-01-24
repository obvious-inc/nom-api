import asyncio
import logging
from typing import List, Union

from app.models.base import APIDocument
from app.models.channel import Channel
from app.models.message import Message
from app.models.user import User
from app.schemas.messages import MessageCreateSchema
from app.services.crud import create_item, get_item_by_id, get_items
from app.services.websockets import broadcast_new_message

logger = logging.getLogger(__name__)


async def create_message(message_model: MessageCreateSchema, current_user: User) -> Union[Message, APIDocument]:
    message = await create_item(item=message_model, result_obj=Message, current_user=current_user, user_field="author")
    asyncio.create_task(broadcast_new_message(str(message.id), str(current_user.id)))
    return message


async def get_messages(channel_id: str, size: int, current_user: User) -> List[Message]:
    channel = await get_item_by_id(id_=channel_id, result_obj=Channel, current_user=current_user)

    # TODO: make sure user can list channel's messages (in server + proper permissions)
    messages = await get_items(
        filters={"channel": channel.id, "server": channel.server.pk},
        result_obj=Message,
        current_user=current_user,
        size=size,
    )
    return messages
