from typing import Union

from starlette.background import BackgroundTasks

from app.helpers.websockets import pusher_client
from app.models.base import APIDocument
from app.models.message import Message
from app.models.server import Server
from app.models.user import User
from app.schemas.messages import MessageCreateSchema
from app.services.crud import create_item, get_items


async def broadcast_message(
    message_model: MessageCreateSchema,
    message: Message,
    current_user: User,
):
    # Server message flows
    # 1. Check server to broadcast to
    # 2. Get members with permission to see channel
    # 3. Check members present (w/ connection open)
    # 4. Broadcast message to their channels

    server = message.server  # type: Server
    members = await get_items(filters={}, result_obj=User, current_user=current_user)
    online_members = members

    event_id = "MESSAGE_CREATE"
    ws_data = {**message_model.dict(), "author": str(current_user.id)}

    # TODO: abstract this away from Pusher specific behaviour
    channels = []
    for online_member in online_members:  # type: User
        channels.extend(online_member.online_channels)

        if len(channels) > 90:
            try:
                await pusher_client.trigger(channels, event_id, ws_data)
            except Exception as e:
                print(f"problems triggering Pusher events: {e}")
            finally:
                channels = []

    if len(channels) > 0:
        try:
            await pusher_client.trigger(channels, event_id, ws_data)
        except Exception as e:
            print(f"problems triggering Pusher events: {e}")


async def create_message(
    message_model: MessageCreateSchema, current_user: User, background_tasks: BackgroundTasks
) -> Union[Message, APIDocument]:
    message = await create_item(item=message_model, result_obj=Message, current_user=current_user, user_field="author")

    background_tasks.add_task(
        broadcast_message, message_model=message_model, message=message, current_user=current_user
    )

    return message
