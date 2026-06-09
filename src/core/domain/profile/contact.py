from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import uuid4


class Contact(BaseModel):
    id: str = Field(alias="_id", default_factory=lambda: str(uuid4()))
    name: str
    channel: Optional[str] = None
    external_id: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
