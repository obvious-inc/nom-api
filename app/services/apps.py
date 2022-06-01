import secrets

from app.models.app import App
from app.models.user import User
from app.models.webhook import Webhook
from app.schemas.apps import AppCreateSchema
from app.schemas.webhooks import WebhookCreateSchema
from app.services.crud import create_item


async def create_app(model: AppCreateSchema, current_user: User):
    model.client_id = secrets.token_urlsafe(16)
    model.client_secret = secrets.token_hex(16)
    return await create_item(item=model, result_obj=App, user_field="creator", current_user=current_user)


async def create_app_webhook(app_id: str, webhook_data: WebhookCreateSchema, current_user: User):
    webhook_data.app = app_id
    webhook_data.secret = secrets.token_urlsafe(32)
    return await create_item(webhook_data, result_obj=Webhook, user_field="creator", current_user=current_user)
