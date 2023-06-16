from umongo import EmbeddedDocument, fields

from app.helpers.db_utils import instance


@instance.register
class PermissionOverwrite(EmbeddedDocument):
    permissions = fields.ListField(fields.StrField)

    role = fields.ReferenceField("Role", required=False)
    group = fields.StrField(required=False)
