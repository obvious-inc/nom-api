from pydantic import Field

from app.models.base import PyObjectId, APIBaseModel


class ServerModel(APIBaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field()

    _collection_name = "servers"

    class Config:
        schema_extra = {
            "example": {
                "name": "Verbs",
            }
        }
