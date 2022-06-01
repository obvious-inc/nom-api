from pymongo import ASCENDING, DESCENDING
from umongo import EmbeddedDocument, fields

from app.helpers.db_utils import instance
from app.models.base import APIDocument


@instance.register
class MessageReaction(EmbeddedDocument):
    emoji = fields.StrField(required=True)
    count = fields.IntField(default=1)
    users = fields.ListField(fields.ReferenceField("User"))


@instance.register
class Message(APIDocument):
    channel = fields.ReferenceField("Channel", required=True)
    server = fields.ReferenceField("Server", required=False, default=None)
    author = fields.ReferenceField("User", required=True)
    type = fields.IntField(default=0)

    content = fields.StrField(required=False, default="")
    blocks = fields.ListField(fields.DictField, default=[])

    edited_at = fields.AwareDateTimeField(required=False, default=None)

    reactions = fields.ListField(fields.EmbeddedField(MessageReaction), default=[])
    embeds = fields.ListField(fields.DictField, default=[])

    reply_to = fields.ReferenceField("Message", required=False, default=None)

    class Meta:
        collection_name = "messages"
        indexes = [
            (("channel", ASCENDING), ("created_at", DESCENDING), ("_id", DESCENDING)),
        ]


@instance.register
class AppMessage(Message):
    author = fields.ReferenceField("User", required=False)
    app = fields.ReferenceField("App", required=True)
    type = fields.IntField(default=3)


@instance.register
class WebhookMessage(AppMessage):
    webhook = fields.ReferenceField("Webhook", required=True)
    type = fields.IntField(default=2)
