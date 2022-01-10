from bson import ObjectId
from pydantic import BaseModel, Field

from app.models.base import PyObjectId


class ServerModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field()

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: ObjectId}
        schema_extra = {
            "example": {
                "name": "Verbs",
            }
        }
