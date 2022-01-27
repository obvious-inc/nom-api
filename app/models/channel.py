from marshmallow import ValidationError
from umongo import fields, validate

from app.helpers.db_utils import instance
from app.models.base import APIDocument
from app.models.server import Server


@instance.register
class Channel(APIDocument):
    kind: str = fields.StrField(validate=validate.OneOf(["dm", "server"]), required=True)  # TODO: make enum?
    owner = fields.ReferenceField("User", required=True)

    last_message_ts = fields.FloatField()

    # DM fields
    members = fields.ListField(fields.ReferenceField("User"))

    # Server fields
    server = fields.ReferenceField(Server)
    name = fields.StrField()

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


@instance.register
class ChannelReadState(APIDocument):
    user = fields.ReferenceField("User")
    channel = fields.ReferenceField("Channel")
    last_read_ts = fields.FloatField()

    class Meta:
        collection_name = "channels_read_states"
