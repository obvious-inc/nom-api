from umongo import EmbeddedDocument, fields

from app.helpers.db_utils import instance


@instance.register
class PermissionOverwrite(EmbeddedDocument):
    role = fields.ReferenceField("Role")
    permissions = fields.ListField(fields.StrField)
