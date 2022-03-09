from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, APIBaseUpdateSchema, PyObjectId


class ServerSchema(APIBaseSchema):
    name: str
    owner: PyObjectId = Field()

    class Config:
        schema_extra = {
            "example": {"id": "61e17018c3ee162141baf5c9", "name": "Verbs", "owner": "61e17018c3ee162141baf5c7"}
        }


class ServerCreateSchema(APIBaseCreateSchema):
    name: str


class ServerMemberSchema(APIBaseSchema):
    server: PyObjectId = Field()
    user: PyObjectId = Field()

    display_name: Optional[str] = Field()
    joined_at: datetime

    class Config:
        schema_extra = {
            "example": {
                "id": "61e17018c3ee162141baf5c9",
                "server": "c3ee162141baf5c1",
                "user": "c3ee162141baf5c1",
                "display_name": "fun.eth",
                "joined_at": "2022-01-01T00:00:00+01:00",
            }
        }


class ServerMemberUpdateSchema(APIBaseUpdateSchema):
    display_name: Optional[str]
