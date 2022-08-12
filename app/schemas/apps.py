from typing import List, Optional

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
    permissions: List[str] = []
    redirect_uris: List[str] = []

    class Config:
        schema_extra = {
            "example": {
                "name": "Github",
                "description": "Github integration for posting events",
                "permissions": ["messages.create"],
            }
        }


class AppInstalledSchema(APIBaseSchema):
    app: PyObjectId
    user: PyObjectId
    channel: PyObjectId

    class Config:
        schema_extra = {
            "example": {
                "app": "",
                "user": "<user_id>",
                "channel": "5e8f8f8f8f8f8f8f8f8f8f8f",
            }
        }


class AppInstalledCreateSchema(APIBaseCreateSchema):
    app: str
    channel: Optional[str]

    class Config:
        schema_extra = {
            "example": {
                "app": "12313123",
                "channel": "123123123123",
            }
        }
