from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, PyObjectId


class MessageReactionSchema(BaseModel):
    emoji: str
    users: List[PyObjectId]
    count: int

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True


class MessageSchema(APIBaseSchema):
    author: PyObjectId = Field()
    server: Optional[PyObjectId] = Field()
    channel: PyObjectId = Field()
    content: str
    reactions: List[MessageReactionSchema]


class MessageCreateSchema(APIBaseCreateSchema):
    server: Optional[str]
    channel: str
    content: str
