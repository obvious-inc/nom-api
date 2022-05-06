from marshmallow import ValidationError
from umongo import fields, validate

from app.helpers.dates import get_mongo_utc_date
from app.helpers.db_utils import instance
from app.models.base import APIDocument
from app.models.user import User


@instance.register
class Server(APIDocument):
    name = fields.StrField(required=True)

    owner = fields.ReferenceField(User, required=True)
    join_rules = fields.ListField(fields.ReferenceField("ServerJoinRule"), default=[], required=False)
    server_token = fields.StrField(required=False)
    description = fields.StrField(required=False)
    avatar = fields.StrField(required=False)
    system_channel = fields.ReferenceField("Channel")

    class Meta:
        collection_name = "servers"


@instance.register
class ServerMember(APIDocument):
    server = fields.ReferenceField(Server, required=True)
    user = fields.ReferenceField(User, required=True)
    owns_token = fields.BoolField(required=False)
    display_name = fields.StrField()
    pfp = fields.DictField()
    joined_at = fields.AwareDateTimeField(default=get_mongo_utc_date)

    class Meta:
        collection_name = "server_members"
        indexes = ["server", "user"]


@instance.register
class ServerJoinRule(APIDocument):
    type: str = fields.StrField(validate=validate.OneOf(["guild_xyz", "allowlist"]), required=True)

    # Guild XYZ fields
    guild_xyz_id = fields.StrField()

    # Allowlist fields
    allowlist_addresses = fields.ListField(fields.StrField)

    def pre_insert(self):
        if self.type == "guild_xyz":
            if not hasattr(self, "guild_xyz_id"):
                raise ValidationError("missing 'guild_xyz_id' field")

        elif self.type == "allowlist":
            if not hasattr(self, "allowlist_addresses"):
                raise ValidationError("missing 'allowlist_addresses' field")

    class Meta:
        collection_name = "server_join_rules"
