import http
from typing import List

from fastapi import APIRouter, Body, Depends

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.apps import AppSchema
from app.schemas.webhooks import WebhookCreateSchema, WebhookSchema
from app.services.apps import create_app_webhook, get_apps

router = APIRouter()


@router.post(
    "/{app_id}/webhooks",
    summary="Create incoming webhook for specific App",
    status_code=http.HTTPStatus.CREATED,
    response_model=WebhookSchema,
)
async def post_create_incoming_webhook(
    app_id: str, webhook_data: WebhookCreateSchema = Body(...), current_user: User = Depends(get_current_user)
):
    return await create_app_webhook(app_id=app_id, webhook_data=webhook_data, current_user=current_user)


@router.get("/", response_description="Get apps", response_model=List[AppSchema])
async def get_fetch_apps():
    return await get_apps()
