from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, PyObjectId


class ChannelSchema(APIBaseSchema):
    kind: str
    owner: PyObjectId = Field()


class DMChannelSchema(ChannelSchema):
    members: List[PyObjectId] = []

    class Config:
        schema_extra = {
            "example": {
                "id": "61e17018c3ee162141baf5c9",
                "kind": "dm",
                "members": ["61e17018c3ee162141baf5c1", "61e17018c3ee162141baf5c2", "61e17018c3ee162141baf5c3"],
                "owner": "61e17018c3ee162141baf5c1",
            }
        }


class ServerChannelSchema(ChannelSchema):
    server: PyObjectId = Field()
    name: str = Field()

    class Config:
        schema_extra = {
            "example": {
                "id": "61e17018c3ee162141baf5c9",
                "kind": "server",
                "name": "🔥-shilling",
                "server": "61e17018c3ee162141baf5c1",
                "owner": "61e17018c3ee162141baf5c1",
            }
        }


class ChannelCreateSchema(APIBaseCreateSchema):
    kind: str


class DMChannelCreateSchema(ChannelCreateSchema):
    kind: str = "dm"
    members: List[str]


class ServerChannelCreateSchema(ChannelCreateSchema):
    kind: str = "server"
    server: str
    name: str


class ChannelReadStateSchema(APIBaseSchema):
    channel: PyObjectId = Field()
    last_read_at: datetime
    mention_count: int = 0


class ChannelReadStateCreateSchema(APIBaseCreateSchema):
    channel: str
    last_read_at: datetime
    mention_count: Optional[int] = 0


# Need this EitherChannel class due to mypy and fastapi issue: https://github.com/tiangolo/fastapi/issues/2279
class EitherChannel(BaseModel):
    __root__: Union[ServerChannelSchema, DMChannelSchema]
