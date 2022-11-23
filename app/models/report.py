from umongo import fields, validate

from app.helpers.db_utils import instance
from app.models.base import APIDocument
from app.models.message import Message
from app.schemas.reports import MessageReportReason, UserReportReason


@instance.register
class MessageReport(APIDocument):
    author = fields.ReferenceField("User", required=True)
    message = fields.ReferenceField(Message, required=True)

    reason = fields.StrField(required=False, validate=validate.OneOf([r for r in MessageReportReason]))
    comment = fields.StrField(required=False)

    class Meta:
        collection_name = "messages_reported"


@instance.register
class UserReport(APIDocument):
    author = fields.ReferenceField("User", required=True)
    user = fields.ReferenceField("User", required=True)

    reason = fields.StrField(required=False, validate=validate.OneOf([r for r in UserReportReason]))
    comment = fields.StrField(required=False)

    class Meta:
        collection_name = "users_reported"
