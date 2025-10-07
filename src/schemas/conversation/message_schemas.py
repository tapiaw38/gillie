from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from fastapi import UploadFile
from src.core.domain import Message


class MessageInput(BaseModel):
    content: str
    context: Optional[str]
    voice_content: Optional[UploadFile] = None


class MessageOutputData(BaseModel):
    id: str
    content: str
    audio_url: Optional[str] = None
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
