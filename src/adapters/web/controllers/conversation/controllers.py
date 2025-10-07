
from fastapi import APIRouter, status, Depends, Request, Query, HTTPException, Form, File, UploadFile
from src.schemas import (
    ConversationInput,
    MessageInput,
)
from src.core.domain import (
    SenderEnum,
)
from src.adapters.services.services import Services
from typing import Optional


router = APIRouter(
    prefix="/conversation",
    tags=["Conversation"],
)

def get_instance() -> Services:
    return Services.get_instance()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation: ConversationInput,
    request: Request,
    service: Services = Depends(get_instance)
):
    user_id = request.state.user.get("user_id")
    conversation = await service.conversation.create(conversation, user_id)
    return conversation

@router.get("/user", status_code=status.HTTP_200_OK)
async def find_conversations_by_user_id(
    request: Request,
    service: Services = Depends(get_instance)
):
    user_id = request.state.user.get("user_id")
    conversations = await service.conversation.find_by_user_id(user_id)
    return conversations

@router.get("/{conversation_id}", status_code=status.HTTP_200_OK)
async def find_conversation_by_id(
    conversation_id: str,
    service: Services = Depends(get_instance)
):
    conversation = await service.conversation.find_by_id(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation

@router.post("/{conversation_id}/message", status_code=status.HTTP_200_OK)
async def add_message(
    conversation_id: str,
    request: Request,
    content: str = Form(...),
    context: Optional[str] = Form(None),
    voice_content: Optional[UploadFile] = File(None),
    service: Services = Depends(get_instance),
    has_image_processor: Optional[str] = Query(None, regex="^(activate|deactivate)$"),
    has_text_to_voice: Optional[str] = Query(None, regex="^(activate|deactivate)$")
):
    sender = SenderEnum.user
    user_id = request.state.user.get("user_id")

    message = MessageInput(
        content=content,
        context=context,
        voice_content=voice_content
    )

    messages = await service.conversation.add_message(
        conversation_id, 
        message, 
        sender, 
        user_id, 
        has_image_processor,
        has_text_to_voice
    )
    return messages

@router.delete("/{conversation_id}/message", status_code=status.HTTP_200_OK)
async def delete_all_messages(
    conversation_id: str,
    request: Request,
    service: Services = Depends(get_instance)
):
    user_id = request.state.user.get("user_id")
    messages = await service.conversation.delete_all_messages(conversation_id, user_id)
    return messages