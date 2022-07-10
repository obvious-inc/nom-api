from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, APIBaseUpdateSchema, PyObjectId


class ChannelSchema(APIBaseSchema):
    kind: str
    owner: PyObjectId = Field()
    last_message_at: Optional[datetime]


class DMChannelSchema(ChannelSchema):
    members: List[PyObjectId] = []
    name: Optional[str]

    class Config:
        schema_extra = {
            "example": {
                "id": "61e17018c3ee162141baf5c9",
                "kind": "dm",
                "members": ["61e17018c3ee162141baf5c1", "61e17018c3ee162141baf5c2", "61e17018c3ee162141baf5c3"],
                "name": "The OG Group",
            }
        }


class ServerChannelSchema(ChannelSchema):
    server: PyObjectId = Field()
    name: str = Field()
    description: Optional[str]

    class Config:
        schema_extra = {
            "example": {
                "id": "61e17018c3ee162141baf5c9",
                "kind": "server",
                "name": "🔥-shilling",
                "description": "Just a good ol' shilling channel",
                "server": "61e17018c3ee162141baf5c1",
                "owner": "61e17018c3ee162141baf5c1",
            }
        }


class TopicChannelSchema(ChannelSchema):
    name: str
    description: Optional[str]
    members: List[PyObjectId] = []
    avatar: Optional[str]

    class Config:
        schema_extra = {
            "example": {
                "id": "61e17018c3ee162141baf5c9",
                "kind": "topic",
                "name": "noun-o-clock",
                "description": "This is a public channel for Noun fans to chat.",
                "avatar": "https://pbs.twimg.com/profile_images/1467601380567359498/oKcnQo_S_400x400.jpg",
                "members": ["61e17018c3ee162141baf5c1", "61e17018c3ee162141baf5c2", "61e17018c3ee162141baf5c3"],
            }
        }


class ChannelCreateSchema(APIBaseCreateSchema):
    kind: str


class DMChannelCreateSchema(ChannelCreateSchema):
    kind: str = "dm"
    members: List[str]


class TopicChannelCreateSchema(ChannelCreateSchema):
    kind: str = "topic"
    name: str
    members: Optional[List[str]] = []
    description: Optional[str] = ""
    avatar: Optional[str] = ""


class ServerChannelCreateSchema(ChannelCreateSchema):
    kind: str = "server"
    server: str
    name: str
    description: Optional[str] = ""


class ChannelReadStateSchema(APIBaseSchema):
    channel: PyObjectId = Field()
    last_read_at: datetime
    mention_count: int = 0


class ChannelReadStateCreateSchema(APIBaseCreateSchema):
    channel: str
    last_read_at: datetime
    mention_count: Optional[int] = 0


class ChannelUpdateSchema(APIBaseUpdateSchema):
    name: Optional[str]
    description: Optional[str]
    avatar: Optional[str]


class ChannelBulkReadStateCreateSchema(APIBaseCreateSchema):
    channels: List[str]
    last_read_at: Optional[datetime]


# Need this EitherChannel class due to mypy and fastapi issue: https://github.com/tiangolo/fastapi/issues/2279
class EitherChannel(BaseModel):
    __root__: Union[TopicChannelSchema, ServerChannelSchema, DMChannelSchema]
