from typing import Optional

from app.models.base import APIBaseModel


class UserModel(APIBaseModel):
    email: Optional[str] = None

    _collection_name = "users"

    class Config:
        schema_extra = {
            "example": {
                "email": "test@newshades.xyz",
            }
        }
