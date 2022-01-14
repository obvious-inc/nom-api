from umongo import fields

from app.helpers.database import instance
from app.models.base import APIDocument


@instance.register
class Server(APIDocument):
    name = fields.StrField()

    class Meta:
        collection_name = "servers"
