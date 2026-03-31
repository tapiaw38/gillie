from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class File(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    name: str
    url: str
    created_at: datetime

    class Config:
        populate_by_name = True
