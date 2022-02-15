from umongo import fields

from app.helpers.dates import get_mongo_utc_date
from app.helpers.db_utils import instance
from app.models.base import APIDocument
from app.models.user import User


@instance.register
class Server(APIDocument):
    name = fields.StrField(required=True)

    owner = fields.ReferenceField(User, required=True)

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
