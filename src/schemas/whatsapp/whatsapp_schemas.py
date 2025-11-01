from pydantic import BaseModel, Field
from typing import Optional


class ProcessExternalMessageRequest(BaseModel):
    """
    Request schema for processing external WhatsApp messages from whatsapp-api-be.

    This schema validates incoming messages from the Go-based whatsapp-api-be service.
    """
    source: str = Field(
        ...,
        description="Message source identifier (e.g., 'whatsapp')",
        examples=["whatsapp"]
    )
    sender: str = Field(
        ...,
        description="Sender phone number in international format",
        examples=["+1234567890"]
    )
    content: str = Field(
        ...,
        description="Message content text",
        min_length=1,
        examples=["Hello, I need help with my order"]
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Existing conversation ID if continuing a conversation (optional)",
        examples=["507f1f77bcf86cd799439011"]
    )
    device_id: str = Field(
        ...,
        description="WhatsApp device ID from whatsapp-api-be service",
        examples=["device-uuid-123"]
    )
    user_id: str = Field(
        ...,
        description="User ID associated with the WhatsApp integration",
        examples=["507f1f77bcf86cd799439012"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source": "whatsapp",
                "sender": "+1234567890",
                "content": "Hello, I need help",
                "conversation_id": None,
                "device_id": "device-uuid-123",
                "user_id": "507f1f77bcf86cd799439012"
            }
        }


class ProcessExternalMessageResponse(BaseModel):
    """
    Response schema for external message processing.

    Returns the conversation ID and the AI-generated assistant response.
    """
    conversation_id: str = Field(
        ...,
        description="Conversation ID (existing or newly created)",
        examples=["507f1f77bcf86cd799439011"]
    )
    assistant_response: str = Field(
        ...,
        description="AI-generated response from the assistant",
        examples=["Hello! How can I assist you today?"]
    )
    status: str = Field(
        default="success",
        description="Processing status",
        examples=["success"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "507f1f77bcf86cd799439011",
                "assistant_response": "Hello! How can I assist you today?",
                "status": "success"
            }
        }
