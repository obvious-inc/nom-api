from umongo import EmbeddedDocument, fields

from app.helpers.db_utils import instance
from app.models.base import APIDocument


@instance.register
class OnlineChannel(EmbeddedDocument):
    channel_name = fields.StrField(required=True)
    provider = fields.StrField(required=True)
    socket_id = fields.StrField(required=False)
    props = fields.DictField(required=False)
    ready = fields.BoolField(default=False)


@instance.register
class User(APIDocument):
    display_name = fields.StrField()

    wallet_address = fields.StrField()
    email = fields.StrField()

    online_channels = fields.ListField(fields.EmbeddedField(OnlineChannel), default=[], required=False)

    class Meta:
        collection_name = "users"
