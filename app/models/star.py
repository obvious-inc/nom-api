from umongo import fields, validate

from app.helpers.db_utils import instance
from app.models.base import APIDocument


@instance.register
class Star(APIDocument):
    type: str = fields.StrField(validate=validate.OneOf(["message", "channel", "server"]), required=True)
    user = fields.ReferenceField("User", required=True)

    message = fields.ReferenceField("Message", required=False, default=None)
    channel = fields.ReferenceField("Channel", required=False, default=None)
    server = fields.ReferenceField("Server", required=False, default=None)

    class Meta:
        collection_name = "stars"
        indexes = ["user"]
