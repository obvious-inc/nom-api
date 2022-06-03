from umongo import fields

from app.helpers.db_utils import instance
from app.models.base import APIDocument


@instance.register
class Webhook(APIDocument):
    secret = fields.StrField()

    creator = fields.ReferenceField("User")
    app = fields.ReferenceField("App")
    channel = fields.ReferenceField("Channel")

    class Meta:
        collection_name = "webhooks"
