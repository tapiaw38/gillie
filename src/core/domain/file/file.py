from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class File(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    name: str
    url: str
    created_at: datetime

    class Config:
        allow_population_by_field_name = True
