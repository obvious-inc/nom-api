from typing import Union

from app.models.base import APIDocument
from app.models.message import Message
from app.models.user import User
from app.schemas.messages import MessageCreateSchema
from app.services.crud import create_item


async def create_message(message_model: MessageCreateSchema, current_user: User) -> Union[Message, APIDocument]:

    # create DB object
    message = await create_item(item=message_model, result_obj=Message, current_user=current_user, user_field="author")

    # push to sockets?

    return message
