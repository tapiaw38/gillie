from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Integration(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    name: str
    type: str
    activated: bool
    config: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        allow_population_by_field_name = True
