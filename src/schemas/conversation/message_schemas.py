from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from fastapi import UploadFile
from src.core.domain import Message


class MessageInput(BaseModel):
    content: str
    context: Optional[str]
    voice_content: Optional[UploadFile] = None
    image_content: Optional[UploadFile] = None
    image_contents: Optional[List[UploadFile]] = None


class MessageImageAnalysisOutput(BaseModel):
    summary: str
    prompt: Optional[str] = None
    extracted_text: Optional[str] = None
    key_findings: Optional[str] = None
    response_context: Optional[str] = None


class MessageImageAttachmentOutput(BaseModel):
    id: str
    name: str
    mime_type: str
    size: int
    storage_key: str
    url: str
    analysis: Optional[MessageImageAnalysisOutput] = None


class MessageOutputData(BaseModel):
    id: str
    content: str
    audio_url: Optional[str] = None
    image_attachments: Optional[List[MessageImageAttachmentOutput]] = None
    sender: str
    created_at: datetime


class MessageOutput(BaseModel):
    data: MessageOutputData

    @staticmethod
    def from_output(message: Message):
        return MessageOutput(
            data=MessageOutputData(
                id=message.id,
                content=message.content,
                audio_url=message.audio_url,
                image_attachments=message.image_attachments,
                sender=message.sender,
                created_at=message.created_at,
            )
        )


class MessageListOutput(BaseModel):
    data: List[MessageOutputData]

    @staticmethod
    def from_output(messages: list[Message]):
        return MessageListOutput(
            data=[MessageOutput.from_output(message).data for message in messages]
        )
