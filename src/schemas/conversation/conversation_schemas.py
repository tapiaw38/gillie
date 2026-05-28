from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from src.core.domain import Conversation, Message, Profile


class ConversationInput(BaseModel):
    title: str
    is_sandbox: bool = False
    contact_id: Optional[str] = None


class ConversationOutputData(BaseModel):
    id: Optional[str]
    title: str
    created_at: datetime
    client_id: str
    profile: Profile
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    messages: Optional[List[Message]]
    is_sandbox: bool = False


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
                contact_id=conversation.contact_id,
                contact_name=conversation.contact_name,
                messages=conversation.messages,
                is_sandbox=conversation.is_sandbox,
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
