from umongo import fields

from app.helpers.db_utils import instance
from app.models.base import APIDocument


@instance.register
class RefreshToken(APIDocument):
    user = fields.ReferenceField("User")
    refresh_token = fields.StrField()

    used = fields.BoolField(default=False)

    class Meta:
        collection_name = "refresh_tokens"
        indexes = ["user"]
