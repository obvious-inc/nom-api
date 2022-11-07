from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, PyObjectId


class StarSchema(APIBaseSchema):
    user: PyObjectId
    type: str
    reference: str


class StarCreateSchema(APIBaseCreateSchema):
    type: str
    reference: str
