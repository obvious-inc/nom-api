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
    join_rules = fields.ListField(fields.ReferenceField("ServerJoinRule"), default=[])

    class Meta:
        collection_name = "servers"


@instance.register
class ServerMember(APIDocument):
    server = fields.ReferenceField(Server, required=True)
    user = fields.ReferenceField(User, required=True)

    display_name = fields.StrField()
    joined_at = fields.AwareDateTimeField(default=get_mongo_utc_date)

    class Meta:
        collection_name = "server_members"


@instance.register
class ServerJoinRule(APIDocument):
    type: str = fields.StrField(validate=validate.OneOf(["guild_xyz", "whitelist"]), required=True)

    # Guild XYZ fields
    guild_xyz_id = fields.StrField()

    # Whitelist fields
    whitelist_addresses = fields.ListField(fields.StrField)

    def pre_insert(self):
        if self.type == "guild_xyz":
            if not hasattr(self, "guild_xyz_id"):
                raise ValidationError("missing 'guild_xyz_id' field")

        elif self.kind == "whitelist":
            if not hasattr(self, "whitelist_addresses"):
                raise ValidationError("missing 'whitelist_addresses' field")

    class Meta:
        collection_name = "server_join_rules"
