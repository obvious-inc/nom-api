from typing import List, Optional

from app.schemas.base import APIBaseCreateSchema, APIBaseUpdateSchema


class PermissionUpdateSchema(APIBaseUpdateSchema):
    role: Optional[str]
    group: Optional[str]
    permissions: List[str]

    class Config:
        schema_extra = {
            "example": [
                {"group": "@public", "permissions": ["messages.list"]},
            ]
        }


class PermissionCreateSchema(APIBaseCreateSchema):
    group: Optional[str]
    permissions: List[str]

    class Config:
        schema_extra = {
            "example": [
                {"group": "@public", "permissions": ["messages.list"]},
            ]
        }
