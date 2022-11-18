from marshmallow import ValidationError
from pymongo import ASCENDING
from umongo import fields, validate

from app.helpers.db_utils import instance
from app.models.base import APIDocument
from app.models.common import PermissionOverwrite
from app.models.server import Server


@instance.register
class Channel(APIDocument):
    kind: str = fields.StrField(validate=validate.OneOf(["dm", "server", "topic"]), required=True)  # TODO: make enum?
    owner = fields.ReferenceField("User")

    last_message_at = fields.AwareDateTimeField()

    # DM / Topic field
    members = fields.ListField(fields.ReferenceField("User"))

    # Server field
    server = fields.ReferenceField(Server)

    name = fields.StrField()
    description = fields.StrField()
    avatar = fields.StrField()

    permission_overwrites = fields.ListField(fields.EmbeddedField(PermissionOverwrite), default=[], load_only=True)

    def pre_insert(self):
        if self.kind == "dm":
            if not hasattr(self, "members"):
                raise ValidationError("missing 'members' field")

        elif self.kind == "server":
            error_fields = []
            if not hasattr(self, "server"):
                error_fields.append("server")
            if not hasattr(self, "name"):
                error_fields.append("name")

            if error_fields:
                raise ValidationError(f"missing fields: {error_fields}")

    class Meta:
        collection_name = "channels"
        indexes = ["server"]


@instance.register
class ChannelReadState(APIDocument):
    user = fields.ReferenceField("User")
    channel = fields.ReferenceField("Channel")
    last_read_at = fields.AwareDateTimeField()
    mention_count = fields.IntField(default=0)

    class Meta:
        collection_name = "channels_read_states"
        indexes = [
            "user",
            [("user", ASCENDING), ("channel", ASCENDING), {"unique": True}],
        ]
