from bson import ObjectId
from pydantic import Field

from app.models.base import PyObjectId, APIBaseModel


class ServerModel(APIBaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field()

    _collection_name = "servers"

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: ObjectId}
        schema_extra = {
            "example": {
                "name": "Verbs",
            }
        }
