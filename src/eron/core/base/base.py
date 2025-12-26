from beanie import Document
from pydantic import Field
from uuid import UUID, uuid4
from pydantic import BaseModel


class BaseCollection(Document):
    id: UUID = Field(default_factory=uuid4, alias="_id")


class BaseResponse(BaseModel):
    id: UUID