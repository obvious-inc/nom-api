from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field


class PyObjectId(ObjectId):

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError('Invalid ObjectID')
        return str(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type='string')


class APIBaseModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    _collection_name: str

    class Config:
        underscore_attrs_are_private = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: ObjectId,
        }

    @property
    def collection_name(self):
        return self._collection_name
