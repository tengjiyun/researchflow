from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CollectionWrite(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator('name', mode='before')
    @classmethod
    def normalise_name(cls, value: object) -> object:
        return ' '.join(value.split()) if isinstance(value, str) else value


class Collection(BaseModel):
    id: int
    name: str
    paper_count: int
    created_at: datetime
    updated_at: datetime


class CollectionList(BaseModel):
    collections: list[Collection]
