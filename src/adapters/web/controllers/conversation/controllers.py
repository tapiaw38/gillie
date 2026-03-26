
from fastapi import APIRouter, status, Depends, Request, Query, HTTPException, Form, File, UploadFile
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
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

    auth_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        auth_token = auth_header.replace("Bearer ", "")

    client_workspace = request.headers.get("X-Gillie-Workspace", "")

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
        has_text_to_voice,
        auth_token,
        client_workspace,
    )
    return messages

class MessageStreamInput(BaseModel):
    content: str

@router.post("/{conversation_id}/message/stream")
async def add_message_stream(
    conversation_id: str,
    request: Request,
    body: MessageStreamInput,
    usecases: Usecases = Depends(get_usecases),
):
    """Stream AI response tokens as Server-Sent Events (SSE).

    Each event is JSON-encoded so newlines inside tokens are safely escaped.
    Client must json.loads() each data payload.
    """
    import json
    user_id = request.state.user.get("user_id")
    client_workspace = request.headers.get("X-Gillie-Workspace", "")
    plan_mode = request.headers.get("X-Gillie-Mode", "") == "plan"

    async def event_generator():
        try:
            async for token in usecases.conversation.add_message_usecase.execute_stream(
                conversation_id=conversation_id,
                content=body.content,
                user_id=user_id,
                client_workspace=client_workspace,
                plan_mode=plan_mode,
            ):
                yield f"data: {json.dumps(token)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps('[ERROR] ' + str(e))}\n\n"
        yield f"data: {json.dumps('[DONE]')}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/tool/approve", status_code=status.HTTP_200_OK)
async def approve_tool(request: Request):
    """Receive user approval or rejection for a pending tool call.

    The CLI sends this request after the user responds to an approval_request
    SSE event. The backend unblocks the waiting tool coroutine with the
    user's decision.

    Body:
        request_id (str):  The UUID from the approval_request event.
        approved   (bool): True to apply the change, False to skip it.
        feedback   (str):  Optional rejection reason (only meaningful when
                           approved is False). The LLM receives this so it
                           can try a different approach.
    """
    from src.core.platform.ai.tools.approval_manager import submit_decision
    body = await request.json()
    request_id = body.get("request_id", "")
    approved = bool(body.get("approved", False))
    feedback = str(body.get("feedback", "") or "")
    found = submit_decision(request_id, approved, feedback)
    return {"ok": found}


@router.post("/{conversation_id}/compact", status_code=status.HTTP_200_OK)
async def compact_conversation(
    conversation_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Force-compact a conversation immediately, regardless of message count."""
    user_id = request.state.user.get("user_id")
    result = await usecases.conversation.add_message_usecase.compact_now(conversation_id, user_id)
    return result


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