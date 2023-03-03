from pymongo import ASCENDING
from umongo import EmbeddedDocument, fields

from app.helpers.db_utils import instance
from app.models.base import APIDocument


@instance.register
class UserAvatar(EmbeddedDocument):
    input = fields.StrField(load_only=True)
    contract = fields.StrField(load_only=True)
    token_id = fields.StrField(load_only=True)
    verified = fields.BoolField()
    input_image_url = fields.StrField()
    token = fields.DictField(load_only=True)
    cf_id = fields.StrField(default="", required=False)

    class Meta:
        strict = False


@instance.register
class User(APIDocument):
    display_name = fields.StrField()
    wallet_address = fields.StrField()
    ens_domain = fields.StrField()
    email = fields.StrField()
    pfp = fields.EmbeddedField(UserAvatar)
    description = fields.StrField()
    status = fields.StrField(default="offline")

    online_channels = fields.ListField(fields.StrField(), required=False, default=[], load_only=True)
    push_tokens = fields.ListField(fields.StrField(), required=False, default=[], load_only=True)
    signers = fields.ListField(fields.StrField(), required=False, default=[], load_only=True)

    class Meta:
        collection_name = "users"
        indexes = [[("wallet_address", ASCENDING)]]


@instance.register
class Role(APIDocument):
    server = fields.ReferenceField("Server")

    name = fields.StrField()
    permissions = fields.ListField(fields.StrField)

    class Meta:
        collection_name = "roles"
        indexes = ["server"]


@instance.register
class UserPreferences(APIDocument):
    user = fields.ReferenceField("User")
    channels = fields.DictField(required=False, default=[])

    class Meta:
        collection_name = "users_preferences"
        indexes = ["user"]


@instance.register
class UserBlock(APIDocument):
    author = fields.ReferenceField("User", required=True)
    user = fields.ReferenceField("User", required=True)

    class Meta:
        collection_name = "users_blocked"


@instance.register
class WhitelistedWallet(APIDocument):
    wallet_address = fields.StrField(required=True)

    class Meta:
        collection_name = "wallets_whitelisted"
        indexes = [[("wallet_address", ASCENDING), {"unique": True}]]
