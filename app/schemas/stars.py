from typing import Optional

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, PyObjectId


class StarSchema(APIBaseSchema):
    user: PyObjectId
    type: str

    server: Optional[PyObjectId]
    channel: Optional[PyObjectId]
    message: Optional[PyObjectId]


class StarCreateSchema(APIBaseCreateSchema):
    server: Optional[str]
    channel: Optional[str]
    message: Optional[str]

    type: Optional[str]
