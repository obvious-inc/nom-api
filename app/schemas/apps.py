from typing import Optional

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, PyObjectId


class AppSchema(APIBaseSchema):
    name: str
    creator: PyObjectId
    description: Optional[str] = ""


class AppCreateSchema(APIBaseCreateSchema):
    name: str = ""
    description: Optional[str] = ""
    client_id: str = ""
    client_secret: str = ""

    class Config:
        schema_extra = {
            "example": {
                "name": "Github",
                "description": "Github integration for posting events",
            }
        }
