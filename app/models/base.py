import datetime

from umongo import Document, MixinDocument, fields

from app.helpers.database import instance


@instance.register
class DatetimeMixin(MixinDocument):
    created_at = fields.DateTimeField(default=datetime.datetime.utcnow)

    # TODO: add default updated_at + trigger on each update
    updated_at = fields.DateTimeField()


@instance.register
class APIDocument(Document, DatetimeMixin):
    class Meta:
        abstract = True
