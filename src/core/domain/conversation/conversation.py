from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .message import Message
from ..profile.profile import Profile


class Conversation(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    title: str
    created_at: datetime
    client_id: str
    profile: Profile
    messages: Optional[List[Message]] = Field(default=None)
    is_sandbox: bool = Field(default=False)
    message_count: Optional[int] = Field(default=0)
    summary: Optional[str] = None
    memory_extracted: bool = Field(default=False)

    class Config:
        populate_by_name = True
