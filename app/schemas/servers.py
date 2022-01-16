from app.schemas.base import APIBaseSchema, APIBaseCreateSchema


class ServerSchema(APIBaseSchema):
    name: str

    class Config:
        schema_extra = {
            "example": {
                "id": "61e17018c3ee162141baf5c9",
                "name": "Verbs",
            }
        }


class ServerCreateSchema(APIBaseCreateSchema):
    name: str
