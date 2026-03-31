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
        populate_by_name = True
