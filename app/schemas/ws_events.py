from datetime import datetime
from typing import List

from pydantic import BaseModel


class EventBase(BaseModel):
    pass


class CreateMarkChannelReadEvent(EventBase):
    channel_ids: List[str]
    last_read_at: datetime
