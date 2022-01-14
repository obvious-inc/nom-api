from umongo import fields

from app.helpers.database import instance
from app.models.base import APIDocument


@instance.register
class User(APIDocument):
    wallet_address = fields.StrField()
    ens_name = fields.StrField()
    email = fields.StrField()

    class Meta:
        collection_name = "users"
