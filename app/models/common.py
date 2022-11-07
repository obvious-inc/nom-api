from umongo import EmbeddedDocument, fields, validate

from app.constants.permissions import MEMBERS_GROUP, OWNERS_GROUP, PUBLIC_GROUP
from app.helpers.db_utils import instance


@instance.register
class PermissionOverwrite(EmbeddedDocument):
    permissions = fields.ListField(fields.StrField)

    role = fields.ReferenceField("Role", required=False)
    group = fields.StrField(required=False, validate=validate.OneOf([MEMBERS_GROUP, PUBLIC_GROUP, OWNERS_GROUP]))
