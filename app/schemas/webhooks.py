from typing import Optional

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, PyObjectId


class WebhookSchema(APIBaseSchema):
    app: PyObjectId
    creator: PyObjectId
    channel: PyObjectId


class WebhookCreatedSchema(APIBaseSchema):
    app: PyObjectId
    creator: PyObjectId
    channel: PyObjectId
    secret: str


class WebhookCreateSchema(APIBaseCreateSchema):
    app: str = ""
    channel: Optional[str]
    secret: str = ""
