from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ApiKey(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    value: str
    description: str
    is_active: bool = True
    created_at: datetime

    class Config:
        populate_by_name = True
