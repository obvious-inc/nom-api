from pydantic import Field

from app.schemas.base import APIBaseSchema, APIBaseCreateSchema, PyObjectId


class ServerSchema(APIBaseSchema):
    name: str
    owner: PyObjectId = Field()

    class Config:
        schema_extra = {
            "example": {
                "id": "61e17018c3ee162141baf5c9",
                "name": "Verbs",
                "owner": "61e17018c3ee162141baf5c7"
            }
        }


class ServerCreateSchema(APIBaseCreateSchema):
    name: str
