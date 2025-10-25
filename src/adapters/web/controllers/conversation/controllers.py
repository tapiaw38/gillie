
from fastapi import APIRouter, status, Depends, Request, Query, HTTPException, Form, File, UploadFile
from src.schemas import (
    ConversationInput,
    MessageInput,
)
from src.core.domain import (
    SenderEnum,
)
from src.core.use_cases.use_cases import Usecases
from typing import Optional


router = APIRouter(
    prefix="/conversation",
    tags=["Conversation"],
)

_usecases_instance = None

def set_usecases(usecases: Usecases):
    """Set the usecases instance (called during app initialization)"""
    global _usecases_instance
    _usecases_instance = usecases

def get_usecases() -> Usecases:
    """Get the usecases instance for dependency injection"""
    if _usecases_instance is None:
        raise Exception("Usecases not initialized. Call set_usecases first.")
    return _usecases_instance

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation: ConversationInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    conversation = usecases.conversation.create_usecase.execute(conversation, user_id)
    return conversation

@router.get("/user", status_code=status.HTTP_200_OK)
async def find_conversations_by_user_id(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
    include_sandbox: bool = Query(
        default=False,
        description="If True, returns ONLY sandbox conversations. If False, returns ONLY production conversations."
    )
):
    user_id = request.state.user.get("user_id")
    conversations = usecases.conversation.find_by_user_id_usecase.execute(user_id, include_sandbox)
    return conversations

@router.get("/{conversation_id}", status_code=status.HTTP_200_OK)
async def find_conversation_by_id(
    conversation_id: str,
    usecases: Usecases = Depends(get_usecases)
):
    conversation = usecases.conversation.find_by_id_usecase.execute(conversation_id)
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
    usecases: Usecases = Depends(get_usecases),
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

    messages = await usecases.conversation.add_message_usecase.execute(
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
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    messages = await usecases.conversation.delete_all_messages_usecase.execute(conversation_id, user_id)
    return messages

@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
async def delete_conversation(
    conversation_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    user_id = request.state.user.get("user_id")
    result = await usecases.conversation.delete_usecase.execute(conversation_id, user_id)
    return result