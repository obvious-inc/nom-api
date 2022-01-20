from typing import Union

from starlette.background import BackgroundTasks

from app.models.base import APIDocument
from app.models.message import Message
from app.models.user import User
from app.schemas.messages import MessageCreateSchema
from app.services.crud import create_item
from app.services.websockets import broadcast_new_message


async def create_message(
    message_model: MessageCreateSchema, current_user: User, background_tasks: BackgroundTasks
) -> Union[Message, APIDocument]:
    message = await create_item(item=message_model, result_obj=Message, current_user=current_user, user_field="author")

    background_tasks.add_task(
        broadcast_new_message, message_model=message_model, message=message, current_user=current_user
    )

    return message
