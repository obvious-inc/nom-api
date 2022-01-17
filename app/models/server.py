from umongo import fields

from app.helpers.database import instance
from app.models.base import APIDocument
from app.models.user import User


@instance.register
class Server(APIDocument):
    name = fields.StrField(required=True)

    owner = fields.ReferenceField(User, required=True)

    class Meta:
        collection_name = "servers"
