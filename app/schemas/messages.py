from datetime import datetime
from typing import List, Optional

from pydantic import Field, root_validator, validator

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, APIBaseUpdateSchema, APIEmbeddedBaseSchema, PyObjectId


class MessageReactionSchema(APIEmbeddedBaseSchema):
    emoji: str
    users: List[PyObjectId]
    count: int


class MessageMentionSchema(APIEmbeddedBaseSchema):
    type: str
    id: PyObjectId


class MessageSchema(APIBaseSchema):
    author: PyObjectId = Field()
    server: Optional[PyObjectId] = Field()
    channel: PyObjectId = Field()
    content: Optional[str]
    blocks: Optional[List[dict]]
    reactions: List[MessageReactionSchema]
    mentions: List[MessageMentionSchema]
    edited_at: Optional[datetime]
    embeds: List[dict]


class MessageCreateSchema(APIBaseCreateSchema):
    server: Optional[str]
    channel: str
    content: Optional[str] = ""
    blocks: Optional[List[dict]] = []

    @root_validator(pre=True)
    def check_blocks_or_content_present(cls, values):
        content = values.get("content", "")
        blocks = values.get("blocks", [])
        if not any([content, blocks]):
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
