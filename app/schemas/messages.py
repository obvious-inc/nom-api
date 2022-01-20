from pydantic import Field

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, PyObjectId


class MessageSchema(APIBaseSchema):
    author: PyObjectId = Field()
    server: PyObjectId = Field()
    channel: PyObjectId = Field()
    content: str


class MessageCreateSchema(APIBaseCreateSchema):
    server: str
    channel: str
    content: str
