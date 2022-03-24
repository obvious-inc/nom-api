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

    async def to_dict(self, expand_fields: List[str] = None, exclude_fields: List[str] = None):
        dumped_obj = self.dump()

        if not expand_fields and not exclude_fields:
            return dumped_obj

        for field, value in self.items():
            if exclude_fields and field in exclude_fields:
                dumped_obj.pop(field, None)
                continue

            if expand_fields and field in expand_fields:
                if isinstance(value, Reference):
                    value = await value.fetch()
                    dumped_obj[field] = await value.to_dict(exclude_fields=exclude_fields)

        return dumped_obj

    class Meta:
        abstract = True
