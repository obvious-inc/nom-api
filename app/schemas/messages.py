from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, root_validator, validator

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, APIBaseUpdateSchema, APIEmbeddedBaseSchema, PyObjectId


class MessageReactionSchema(APIEmbeddedBaseSchema):
    emoji: str
    users: List[PyObjectId]
    count: int


class MessageSchema(APIBaseSchema):
    author: Optional[PyObjectId] = Field()
    server: Optional[PyObjectId] = Field()
    channel: PyObjectId = Field()
    content: Optional[str]
    blocks: Optional[List[dict]]
    reactions: List[MessageReactionSchema]
    edited_at: Optional[datetime]
    embeds: List[dict]
    reply_to: Optional[PyObjectId]
    inviter: Optional[PyObjectId]
    updates: Optional[dict]
    type: Optional[int] = 0


class MessageCreateSchema(APIBaseCreateSchema):
    server: Optional[str]
    channel: Optional[str]
    content: Optional[str] = ""
    blocks: Optional[List[dict]] = []
    reply_to: Optional[str]
    type: Optional[int] = 0

    @root_validator(pre=True)
    def check_blocks_or_content_present(cls, values):
        content = values.get("content", "")
        blocks = values.get("blocks", [])
        if not any([content, blocks]) and values.get("type", 0) == 0:
            raise ValueError("either 'blocks' or 'content' is required")
        return values


class MessageUpdateSchema(APIBaseUpdateSchema):
    content: Optional[str] = ""
    blocks: Optional[List[dict]] = []

    @validator("content", pre=True)
    def check_content_not_empty(cls, v):
        if v == "":
            raise ValueError("content can't be empty string")
        return v

    @validator("blocks", pre=True)
    def check_blocks_not_empty(cls, v):
        if len(v) == 0:
            raise ValueError("blocks can't be empty list")
        return v


class SystemMessageCreateSchema(MessageCreateSchema):
    channel: Optional[str]
    server: Optional[str]
    inviter: Optional[str]
    updates: Optional[dict] = {}
    type: int = 1


class AppMessageCreateSchema(MessageCreateSchema):
    app: Optional[str]
    channel: Optional[str]
    type: int = 3


class AppMessageSchema(MessageSchema):
    app: PyObjectId = Field()
    type: Optional[int] = 3


class WebhookMessageCreateSchema(AppMessageCreateSchema):
    webhook: Optional[str]
    type: int = 2


class WebhookMessageSchema(AppMessageSchema):
    webhook: PyObjectId = Field()
    type: Optional[int] = 2


class EitherMessage(BaseModel):
    __root__: Union[WebhookMessageSchema, AppMessageSchema, MessageSchema]
