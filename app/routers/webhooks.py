import logging
from typing import Optional

from fastapi import APIRouter, Body, Header, HTTPException, Request
from sentry_sdk import capture_exception
from starlette import status

from app.helpers.queue_utils import queue_bg_task
from app.helpers.websockets import pusher_client
from app.models.webhook import Webhook
from app.schemas.messages import WebhookMessageCreateSchema
from app.services.crud import get_item_by_id
from app.services.messages import create_webhook_message
from app.services.webhooks import handle_pusher_event

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/pusher", include_in_schema=False)
async def post_pusher_webhooks(
    request: Request, x_pusher_key: Optional[str] = Header(None), x_pusher_signature: Optional[str] = Header(None)
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


@router.post("/{webhook_id}/{secret}")
async def post_create_webhook_message_with_secret(
    webhook_id: str, secret: str, message: WebhookMessageCreateSchema = Body(...)
):
    webhook = await get_item_by_id(id_=webhook_id, result_obj=Webhook)
    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Could not found webhook")

    if webhook.secret != secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    message.channel = webhook.channel
    message.app = str(webhook.app.pk)
    message.webhook = webhook_id

    try:
        # TODO queue this
        await create_webhook_message(message_model=message, ignore_permissions=True)
    except Exception as e:
        logger.exception(e)
        capture_exception(e)
        return {"status": "not ok"}

    return {"status": "ok"}
