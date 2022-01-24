from umongo import fields

from app.helpers.db_utils import instance
from app.models.base import APIDocument
from app.models.channel import Channel
from app.models.server import Server
from app.models.user import User


@instance.register
class Message(APIDocument):
    channel = fields.ReferenceField(Channel, required=False)
    server = fields.ReferenceField(Server, required=False)
    author = fields.ReferenceField(User, required=True)

    content = fields.StrField()  # TODO: prolly not only a string

    class Meta:
        collection_name = "messages"
