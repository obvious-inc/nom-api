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
    content: str
    reactions: List[MessageReactionSchema]
    mentions: List[MessageMentionSchema]
    edited_at: Optional[datetime]


class MessageCreateSchema(APIBaseCreateSchema):
    server: Optional[str]
    channel: str
    content: str


class MessageUpdateSchema(APIBaseUpdateSchema):
    content: Optional[str]
