from umongo import fields, validate

from app.helpers.db_utils import instance
from app.models.base import APIDocument


@instance.register
class Star(APIDocument):
    user = fields.ReferenceField("User", required=True)

    type: str = fields.StrField(
        validate=validate.OneOf(["message", "channel", "user", "wallet_address"]), required=True
    )
    reference = fields.StrField(required=True)

    class Meta:
        collection_name = "stars"
        indexes = ["user"]
