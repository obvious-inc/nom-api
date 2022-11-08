from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, PyObjectId


class ChannelPreferencesSchema(BaseModel):
    muted: bool
    muted_until: Optional[datetime]


class UserPreferencesSchema(APIBaseSchema):
    user: PyObjectId
    channels: Dict[PyObjectId, ChannelPreferencesSchema]


class ChannelPreferencesUpdateSchema(BaseModel):
    muted: Optional[bool] = False
    muted_until: Optional[datetime] = None


class UserPreferencesUpdateSchema(APIBaseCreateSchema):
    channels: Optional[Dict[str, ChannelPreferencesUpdateSchema]]
