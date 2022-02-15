from typing import List

from umongo import Document, MixinDocument, Reference, fields

from app.helpers.dates import get_mongo_utc_date
from app.helpers.db_utils import instance


@instance.register
class DatetimeMixin(MixinDocument):
    created_at = fields.AwareDateTimeField(default=get_mongo_utc_date)

    # TODO: add default updated_at + trigger on each update
    updated_at = fields.AwareDateTimeField()


@instance.register
class APIDocument(Document, DatetimeMixin):
    deleted = fields.BoolField(default=False)

    async def to_dict(self, expand: bool = False, expand_fields: List[str] = None):
        dumped_obj = self.dump()
        if not expand:
            return dumped_obj

        for field, value in self.items():
            if expand_fields and field not in expand_fields:
                continue

            if isinstance(value, Reference):
                value = await value.fetch()
                dumped_obj[field] = value.dump()

        return dumped_obj

    class Meta:
        abstract = True
