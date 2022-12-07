from typing import Dict, Optional

from pydantic import BaseModel

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, PyObjectId


class ChannelPreferencesSchema(BaseModel):
    muted: Optional[bool]
    mentions: Optional[bool]
    dismissed: Optional[bool]


class UserPreferencesSchema(APIBaseSchema):
    user: PyObjectId
    channels: Dict[PyObjectId, ChannelPreferencesSchema]


class ChannelPreferencesUpdateSchema(BaseModel):
    muted: Optional[bool]
    mentions: Optional[bool]
    dismissed: Optional[bool]


class UserPreferencesUpdateSchema(APIBaseCreateSchema):
    channels: Optional[Dict[str, ChannelPreferencesUpdateSchema]]
