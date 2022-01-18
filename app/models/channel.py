from umongo import fields, validate

from app.helpers.database import instance
from app.models.base import APIDocument
from app.models.server import Server
from app.models.user import User


@instance.register
class Channel(APIDocument):
    kind: str = fields.StrField(validate=validate.OneOf(["dm", "server"]), required=True)  # TODO: make enum?
    owner = fields.ReferenceField(User, required=True)

    class Meta:
        abstract = True


@instance.register
class DMChannel(Channel):
    members = fields.ListField(fields.ReferenceField(User), required=True)

    class Meta:
        collection_name = "channels"


@instance.register
class ServerChannel(Channel):
    server = fields.ReferenceField(Server, required=True)
    name = fields.StrField(required=True)

    class Meta:
        collection_name = "channels"
