from fastapi import APIRouter, status, Depends, Request, Query, Form, File, UploadFile
from fastapi.responses import StreamingResponse
from src.schemas import (
    ConversationInput,
    MessageInput,
)
from src.core.domain import (
    SenderEnum,
)
from src.core.use_cases.use_cases import Usecases
from src.adapters.web.dependencies import get_usecases
from typing import Optional
import logging
import os


router = APIRouter(
    prefix="/conversation",
    tags=["Conversation"],
)
logger = logging.getLogger(__name__)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation: ConversationInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id")
    conversation = await usecases.conversation.create_usecase.execute(
        conversation,
        user_id,
    )
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
    conversations = await usecases.conversation.find_by_user_id_usecase.execute(
        user_id,
        include_sandbox,
    )
    return conversations

@router.get("/{conversation_id}", status_code=status.HTTP_200_OK)
async def find_conversation_by_id(
    conversation_id: str,
    usecases: Usecases = Depends(get_usecases),
):
    return await usecases.conversation.find_by_id_usecase.execute(conversation_id)

@router.post("/{conversation_id}/message", status_code=status.HTTP_200_OK)
async def add_message(
    conversation_id: str,
    request: Request,
    content: str = Form(...),
    context: Optional[str] = Form(None),
    voice_content: Optional[UploadFile] = File(None),
    image_content: Optional[UploadFile] = File(None),
    files: Optional[list[UploadFile]] = File(None),
    document_content: Optional[UploadFile] = File(None),
    usecases: Usecases = Depends(get_usecases),
    has_image_processor: Optional[str] = Query(None, regex="^(activate|deactivate)$"),
    has_text_to_voice: Optional[str] = Query(None, regex="^(activate|deactivate)$")
):
    sender = SenderEnum.user
    user_id = request.state.user.get("user_id")

    if document_content:
        filename = os.path.basename(document_content.filename or "")
        extension = os.path.splitext(filename)[1].lower()
        if extension not in {".pdf", ".docx"}:
            from fastapi import HTTPException
            raise HTTPException(status_code=415, detail="Only PDF and DOCX documents are supported")

        # Keep multipart document handling inside Gillie so its existing PDF,
        # OCR, DOCX and RAG tools can access the uploaded file by name.
        from src.schemas import FileInput
        uploaded = await usecases.profile.add_files_usecase.execute(
            user_id,
            [FileInput(document_content)],
        )
        if not uploaded.data:
            from fastapi import HTTPException
            raise HTTPException(status_code=502, detail="Document upload failed")

        stored_name = uploaded.data[-1].name
        content = (
            f"{content}\n\n"
            f"[Documento adjunto: {filename}; archivo interno: {stored_name}]\n"
            "Usá las herramientas documentales disponibles para leerlo."
        )

    auth_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        auth_token = auth_header.replace("Bearer ", "")

    client_workspace = request.headers.get("X-Gillie-Workspace", "")

    message = MessageInput(
        content=content,
        context=context,
        voice_content=voice_content,
        image_content=image_content,
        image_contents=files,
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

@router.post("/{conversation_id}/transcribe")
async def transcribe_voice(
    conversation_id: str,
    request: Request,
    voice_content: UploadFile = File(...),
    language: Optional[str] = Form(default=None),
    usecases: Usecases = Depends(get_usecases),
):
    """Transcribe a recording without generating a reply.

    `language` is the language being spoken. It defaults to the profile's, but
    a client listening to a call in another language can override it without
    changing the language its replies come back in.
    """
    user_id = request.state.user.get("user_id")
    text = await usecases.conversation.add_message_usecase.transcribe(
        voice_content, user_id, language
    )
    return {"data": {"text": text or ""}}


@router.post("/{conversation_id}/message/stream")
async def add_message_stream(
    conversation_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
    content: Optional[str] = Form(default=None),
    context: Optional[str] = Form(default=None),
    has_text_to_voice: Optional[str] = Query(None, regex="^(activate|deactivate)$"),
    voice_content: Optional[UploadFile] = File(None),
    image_content: Optional[UploadFile] = File(None),
    files: Optional[list[UploadFile]] = File(None),
):
    """Stream AI response tokens as Server-Sent Events (SSE).

    Accepts both form-encoded (CLI) and JSON body (UI) requests.
    Each event is JSON-encoded so newlines inside tokens are safely escaped.
    Client must json.loads() each data payload.
    """
    import json
    # Support JSON body (UI) when form field is absent
    if content is None:
        try:
            body = await request.json()
            content = body.get("content", "")
            context = body.get("context")
        except Exception:
            content = ""

    user_id = request.state.user.get("user_id")
    client_workspace = request.headers.get("X-Gillie-Workspace", "")
    plan_mode = request.headers.get("X-Gillie-Mode", "") == "plan"
    run_id = request.headers.get("X-Gillie-Run-Id", "") or None
    auth_header = request.headers.get("Authorization", "")
    auth_token = auth_header.replace("Bearer ", "") if auth_header else None
    async def event_generator():
        try:
            async for token in usecases.conversation.add_message_usecase.execute_stream(
                conversation_id=conversation_id,
                content=content,
                user_id=user_id,
                client_workspace=client_workspace,
                plan_mode=plan_mode,
                auth_token=auth_token,
                has_text_to_voice=has_text_to_voice,
                message=MessageInput(
                    content=content or "",
                    context=context,
                    voice_content=voice_content,
                    image_content=image_content,
                    image_contents=files,
                ),
                run_id=run_id,
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
    found = await submit_decision(request_id, approved, feedback)
    return {"ok": found}



@router.post("/{conversation_id}/compact", status_code=status.HTTP_200_OK)
async def compact_conversation(
    conversation_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Force-compact a conversation immediately, regardless of message count."""
    user_id = request.state.user.get("user_id")
    result = await usecases.conversation.compact_usecase.execute(conversation_id, user_id)
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
