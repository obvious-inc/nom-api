from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class EventBase(BaseModel):
    pass


class CreateMarkChannelReadEvent(EventBase):
    channel_id: Optional[str]
    channel_ids: Optional[List[str]]
    last_read_at: datetime
