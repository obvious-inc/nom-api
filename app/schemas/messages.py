from datetime import datetime
from typing import List, Optional

from pydantic import Field

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
    content: Optional[str]
    blocks: List[dict]


class MessageUpdateSchema(APIBaseUpdateSchema):
    content: Optional[str]
    blocks: Optional[List[dict]]
