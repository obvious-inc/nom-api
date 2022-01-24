import asyncio
import logging
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from starlette import status

from app.helpers.connection import get_db
from app.helpers.websockets import pusher_client
from app.models.user import User
from app.services.users import get_user_by_id
from app.services.websockets import broadcast_connection_ready

logger = logging.getLogger(__name__)

router = APIRouter()


async def process_webhook_events(events: list[dict]):
    for event in events:
        try:
            channel_name = event["channel"]
            user_id = channel_name.split("-")[1]
            if event["name"] == "channel_occupied":
                update_data = {"$addToSet": {"online_channels": channel_name}}
            elif event["name"] == "channel_vacated":
                update_data = {"$pull": {"online_channels": channel_name}}
            elif event["name"] == "client_event":
                client_event = event["event"]
                if client_event == "client-connection-request":
                    user = await get_user_by_id(user_id)
                    if not user:
                        raise Exception(f"Missing user. [user_id={user_id}]")
                    await broadcast_connection_ready(current_user=user, channel=channel_name)
                return
            else:
                raise NotImplementedError(f"not expected event: {event}")

            await User.collection.update_one(filter={"_id": ObjectId(user_id)}, update=update_data)
        except Exception:
            logger.exception("Problems handling webhook event. [event=%(name)s, channel=%(channel)s]", event)


@router.post("/pusher", include_in_schema=False)
async def post_pusher_webhooks(
    request: Request,
    x_pusher_key: Optional[str] = Header(None),
    x_pusher_signature: Optional[str] = Header(None),
    db=Depends(get_db),
):
    webhook_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate webhook",
    )

    # need to use raw body
    data = await request.body()
    try:
        webhook = pusher_client.validate_webhook(key=x_pusher_key, signature=x_pusher_signature, body=data)
        if not webhook:
            raise Exception("No valid webhook extracted.")
    except Exception as e:
        logger.exception("Error validating webhook signature.")
        raise webhook_exception

    asyncio.create_task(process_webhook_events(events=webhook["events"]))

    return {"received": "ok"}
