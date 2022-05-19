from typing import List, Optional

from app.schemas.base import APIBaseCreateSchema, APIBaseSchema, APIBaseUpdateSchema, PyObjectId


class SectionSchema(APIBaseSchema):
    name: str
    server: PyObjectId
    channels: List[PyObjectId]

    position: Optional[int]

    class Config:
        schema_extra = {
            "example": {
                "name": "community",
                "server": "61e17018c3ee162141baf5c7",
                "channels": ["61e17018c3ee162141baf5c1", "61e17018c3ee162141baf5c2", "61e17018c3ee162141baf5c3"],
                "position": 0,
            }
        }


class SectionCreateSchema(APIBaseCreateSchema):
    name: str
    channels: Optional[List[str]] = []
    server: Optional[str]
    position: Optional[int] = 0


class SectionUpdateSchema(APIBaseUpdateSchema):
    name: Optional[str]
    channels: Optional[List[str]]


class SectionServerUpdateSchema(APIBaseUpdateSchema):
    id: str
    name: Optional[str]
    channels: Optional[List[str]]
    position: Optional[int]
