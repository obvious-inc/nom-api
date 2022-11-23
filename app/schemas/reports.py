from enum import Enum
from typing import Optional

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, PyObjectId


class MessageReportReason(str, Enum):
    SPAM = "spam"
    ABUSE = "abuse"
    OTHER = "other"


class UserReportReason(str, Enum):
    SPAM = "spam"
    ABUSE = "abuse"
    OTHER = "other"


class MessageReportCreateSchema(APIBaseCreateSchema):
    message: Optional[str] = ""
    reason: Optional[MessageReportReason] = MessageReportReason.OTHER
    comment: Optional[str] = ""

    class Config:
        use_enum_values = True


class MessageReportSchema(APIBaseSchema):
    message: PyObjectId
    author: PyObjectId
    reason: Optional[str]
    comment: Optional[str]


class UserReportCreateSchema(APIBaseCreateSchema):
    user: str
    reason: Optional[UserReportReason] = UserReportReason.OTHER
    comment: Optional[str] = ""

    class Config:
        use_enum_values = True


class UserReportSchema(APIBaseSchema):
    user: PyObjectId
    author: PyObjectId
    reason: Optional[str]
    comment: Optional[str]
