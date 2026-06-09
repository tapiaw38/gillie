from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import uuid4
from ..common.enums import SenderEnum


class ImageAnalysis(BaseModel):
    summary: str
    prompt: Optional[str] = None
    extracted_text: Optional[str] = None
    key_findings: Optional[str] = None
    response_context: Optional[str] = None


class MessageImageAttachment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    mime_type: str
    size: int
    storage_key: str
    url: str
    analysis: Optional[ImageAnalysis] = None


class Message(BaseModel):
    id: str = Field(
        alias="_id",
        default_factory=lambda: str(uuid4()),
    )
    content: str
    audio_url: Optional[str] = None
    image_attachments: Optional[List[MessageImageAttachment]] = None
    sender: SenderEnum
    created_at: datetime
