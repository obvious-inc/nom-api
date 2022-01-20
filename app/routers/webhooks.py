from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from starlette import status
from starlette.background import BackgroundTasks

from app.helpers.database import get_db
from app.helpers.websockets import pusher_client
from app.models.user import User

router = APIRouter()


async def process_webhook_events(events: list[dict], db):
    for event in events:
        try:
            channel_name = event["channel"]
            user_id = channel_name.split("-")[1]
            if event["name"] == "channel_occupied":
                update_data = {"$addToSet": {"online_channels": channel_name}}
            elif event["name"] == "channel_vacated":
                update_data = {"$pull": {"online_channels": channel_name}}
            else:
                raise NotImplementedError(f"not expected event: {event}")

            await User.collection.update_one(filter={"_id": ObjectId(user_id)}, update=update_data)
        except Exception as e:
            print(f"problems handling event {event}: {e}")


@router.post("/pusher", include_in_schema=False)
async def post_pusher_webhooks(
    request: Request,
    x_pusher_key: Optional[str] = Header(None),
    x_pusher_signature: Optional[str] = Header(None),
    db=Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    webhook_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate webhook",
    )

    # need to use raw body
    data = await request.body()
    try:
        webhook = pusher_client.validate_webhook(key=x_pusher_key, signature=x_pusher_signature, body=data)
    except Exception as e:
        raise webhook_exception

    if not webhook:
        raise webhook_exception

    background_tasks.add_task(process_webhook_events, events=webhook["events"], db=db)

    return {"received": "ok"}
