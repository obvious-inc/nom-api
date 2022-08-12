from umongo import fields

from app.helpers.db_utils import instance
from app.models.base import APIDocument


@instance.register
class App(APIDocument):
    name = fields.StrField()
    creator = fields.ReferenceField("User")
    description = fields.StrField(required=False)
    client_id = fields.StrField()
    client_secret = fields.StrField()
    redirect_uris = fields.ListField(fields.StrField(), default=[])

    permissions = fields.ListField(fields.StrField)

    class Meta:
        collection_name = "apps"


@instance.register
class AppInstalled(APIDocument):
    app = fields.ReferenceField("App")
    user = fields.ReferenceField("User")
    channel = fields.ReferenceField("Channel")

    class Meta:
        collection_name = "apps_installed"
