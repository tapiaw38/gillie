from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import uuid4
from ..common.enums import SenderEnum


class Message(BaseModel):
    id: str = Field(
        alias="_id",
        default_factory=lambda: str(uuid4()),
    )
    content: str
    audio_url: Optional[str] = None
    sender: SenderEnum
    created_at: datetime
