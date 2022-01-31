from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field
from umongo.frameworks.motor_asyncio import MotorAsyncIOReference


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, MotorAsyncIOReference):
            v = v.pk
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectID")
        return str(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class APIBaseSchema(BaseModel):
    id: PyObjectId = Field()
    created_at: datetime
    updated_at: Optional[datetime] = None  # TODO: fix this in umongo doc
    deleted: bool = False

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True


class APIBaseCreateSchema(BaseModel):
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
