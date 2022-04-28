from umongo import fields

from app.helpers.db_utils import instance
from app.models.base import APIDocument


@instance.register
class Section(APIDocument):
    name = fields.StrField(required=True)
    server = fields.ReferenceField("Server")
    channels = fields.ListField(fields.ReferenceField("Channel"), default=[])

    position = fields.IntField()

    class Meta:
        collection_name = "sections"
        indexes = ["server"]
