import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from starlette import status

from app.helpers.connection import get_db
from app.helpers.queue_utils import queue_bg_task
from app.helpers.websockets import pusher_client
from app.services.webhooks import handle_pusher_event

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/pusher", include_in_schema=False)
async def post_pusher_webhooks(
    request: Request,
    x_pusher_key: Optional[str] = Header(None),
    x_pusher_signature: Optional[str] = Header(None),
    db=Depends(get_db),
):
    # need to use raw body
    data = await request.body()
    try:
        webhook = pusher_client.validate_webhook(key=x_pusher_key, signature=x_pusher_signature, body=data)
        if not webhook:
            raise Exception("No valid webhook extracted.")
    except Exception:
        logger.exception("Error validating webhook signature.")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate webhook",
        )

    [await queue_bg_task(handle_pusher_event, event) for event in webhook["events"]]

    return {"received": "ok"}
