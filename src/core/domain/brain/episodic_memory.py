from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EpisodicMemory(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    type: str = "episode"  # "episode" | "fact" | "preference" | "goal"
    content: str
    importance: int = Field(default=5, ge=1, le=10)
    emotion: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    source_conversation_id: Optional[str] = None
    created_at: datetime
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    promoted_to_soul: bool = False

    class Config:
        populate_by_name = True
