from umongo import fields

from app.helpers.db_utils import instance
from app.models.base import APIDocument


@instance.register
class RefreshToken(APIDocument):
    user = fields.ReferenceField("User", default=None, required=False)
    app = fields.ReferenceField("App", default=None, required=False)
    refresh_token = fields.StrField()
    scopes = fields.ListField(fields.StrField(), default=[])

    used = fields.BoolField(default=False)

    class Meta:
        collection_name = "refresh_tokens"
        indexes = ["user"]


@instance.register
class AuthorizationCode(APIDocument):
    user = fields.ReferenceField("User")
    app = fields.ReferenceField("App")
    client_id = fields.StrField()
    code = fields.StrField()
    redirect_uri = fields.StrField()
    response_type = fields.StrField()
    scope = fields.StrField()
    expires_in = fields.IntField()
    auth_time = fields.IntField()
    nonce = fields.StrField(required=False, default=None)

    class Meta:
        collection_name = "auth_codes"
