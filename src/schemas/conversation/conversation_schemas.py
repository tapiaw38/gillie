from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from src.core.domain import Conversation, Message, Profile


class ConversationInput(BaseModel):
    title: str


class ConversationOutputData(BaseModel):
    id: Optional[str]
    title: str
    created_at: datetime
    client_id: str
    profile: Profile
    messages: Optional[List[Message]]


class ConversationOutput(BaseModel):
    data: ConversationOutputData

    @staticmethod
    def from_output(conversation: Conversation):
        return ConversationOutput(
            data=ConversationOutputData(
                id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at,
                client_id=conversation.client_id,
                profile=conversation.profile,
                messages=conversation.messages,
            )
        )


class ConversationListOutput(BaseModel):
    data: List[ConversationOutputData]

    @staticmethod
    def from_output(conversations: list[Conversation]):
        return ConversationListOutput(
            data=[
                ConversationOutput.from_output(conversation).data
                for conversation in conversations
            ]
        )
