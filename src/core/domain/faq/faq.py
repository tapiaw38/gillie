from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FAQ(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    question: str
    answer: str
    category: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    is_active: Optional[bool] = Field(default=True)
    order: Optional[int] = Field(default=0)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    class Config:
        allow_population_by_field_name = True
