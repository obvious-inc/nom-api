from umongo import fields

from app.helpers.database import instance
from app.models.base import APIDocument


@instance.register
class User(APIDocument):
    display_name = fields.StrField()

    wallet_address = fields.StrField()
    email = fields.StrField()

    online_channels = fields.ListField(fields.StrField(), required=False, default=[])

    class Meta:
        collection_name = "users"
