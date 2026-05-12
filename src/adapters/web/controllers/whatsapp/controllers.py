from fastapi import APIRouter, Depends, Body, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import PlainTextResponse, JSONResponse
from src.adapters.web.dependencies import get_usecases
from src.core.use_cases.use_cases import Usecases
from src.schemas import (
    ProcessExternalMessageRequest,
    ProcessExternalMessageResponse,
    ConversationInput,
    MessageInput,
)
from src.core.domain import SenderEnum
from typing import Dict, Any, Deque, Optional
import logging
import json
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)
last_payloads = deque(maxlen=10)
router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])


def _extract_bearer_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    return None


def _build_test_payload(phone_number: str, message: str) -> Dict[str, Any]:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": phone_number,
                                    "id": f"test-{phone_number}",
                                    "timestamp": "0",
                                    "type": "text",
                                    "text": {"body": message},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


async def _find_active_whatsapp_profile(usecases: Usecases):
    profile = await usecases.profile.find_with_active_whatsapp_integration_usecase.execute()
    if not profile:
        return None
    for integration in profile.integrations or []:
        if integration.name == "whatsapp" and integration.activated:
            return profile
    return None


async def _resolve_external_conversation_id(
    usecases: Usecases,
    request: ProcessExternalMessageRequest,
) -> str:
    conversation_title = f"WhatsApp-{request.sender}"
    conversation_id = None

    if request.conversation_id:
        try:
            await usecases.conversation.find_by_id_usecase.execute(request.conversation_id)
            conversation_id = request.conversation_id
            logger.info("Using existing conversation: %s", conversation_id)
        except HTTPException as exc:
            if exc.status_code == 404:
                logger.warning(
                    "Conversation %s not found, will create new one",
                    request.conversation_id,
                )
            else:
                raise

    if not conversation_id:
        conversation_list = await usecases.conversation.find_by_user_id_usecase.execute(request.user_id)
        for conversation_data in conversation_list.data:
            if conversation_title == conversation_data.title:
                conversation_id = conversation_data.id
                logger.info("Found existing conversation by title: %s", conversation_id)
                break

    if conversation_id:
        return conversation_id

    logger.info("Creating new conversation: %s", conversation_title)
    new_conversation = await usecases.conversation.create_usecase.execute(
        ConversationInput(title=conversation_title),
        request.user_id,
    )
    conversation_id = new_conversation.data.id
    logger.info("Created new conversation: %s", conversation_id)
    return conversation_id


def _extract_last_assistant_response(updated_conversation, conversation_id: str) -> str:
    if not updated_conversation or not updated_conversation.data.messages:
        logger.error("Could not retrieve updated conversation %s", conversation_id)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation after processing message",
        )

    assistant_messages = [
        msg
        for msg in updated_conversation.data.messages
        if msg.sender == SenderEnum.assistant
    ]
    if not assistant_messages:
        logger.warning("No assistant messages found in conversation %s", conversation_id)
        return "I apologize, but I couldn't generate a response at this moment."

    assistant_response = assistant_messages[-1].content
    logger.info(
        "AI response generated: %s",
        f"{assistant_response[:100]}..." if len(assistant_response) > 100 else assistant_response,
    )
    return assistant_response


def _extract_business_account_id(payload: Dict[Any, Any]) -> str:
    try:
        logger.debug("Estructura del payload: %s", payload)

        if "entry" in payload and len(payload["entry"]) > 0:
            entry = payload["entry"][0]
            logger.debug("Entry encontrado: %s", entry)

            if "changes" in entry and len(entry["changes"]) > 0:
                value = entry["changes"][0]["value"]
                logger.debug("Value encontrado: %s", value)

                if "metadata" in value and "business_account_id" in value["metadata"]:
                    return value["metadata"]["business_account_id"]
                if "metadata" in value and "phone_number_id" in value["metadata"]:
                    return value["metadata"]["phone_number_id"]
                if "phone_number_id" in value:
                    return value["phone_number_id"]

        if "phone_number_id" in payload:
            return payload["phone_number_id"]

        def search_for_id(obj, keys=("business_account_id", "phone_number_id", "from_id")):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in keys and value:
                        return value
                    result = search_for_id(value, keys)
                    if result:
                        return result
            elif isinstance(obj, list):
                for item in obj:
                    result = search_for_id(item, keys)
                    if result:
                        return result
            return None

        found = search_for_id(payload)
        if found:
            return found
    except (KeyError, IndexError) as exc:
        logger.error("Error al obtener business_account_id: %s", str(exc))
        logger.debug("Payload structure: %s", payload)

    logger.warning("Could not find business ID, using 'default' for debugging")
    return "default"


async def _resolve_webhook_profile(usecases: Usecases, business_account_id: str):
    if business_account_id == "default":
        logger.info("Looking for a profile with any active WhatsApp integration")
        return await usecases.profile.find_with_active_whatsapp_integration_usecase.execute()

    profile = await usecases.profile.find_by_whatsapp_business_id_usecase.execute(
        business_account_id,
    )
    if profile:
        return profile

    logger.warning(
        "No profile found with business_account_id: %s, searching for profiles with active WhatsApp",
        business_account_id,
    )
    return await usecases.profile.find_with_active_whatsapp_integration_usecase.execute()


@router.get("/verify", response_class=PlainTextResponse)
async def verify_endpoint():
    logger.info("Simple verification request received")
    return "WhatsApp webhook server is running"


@router.post("/transcribe-audio")
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(...),
    language: str = Form("es-ES"),
    usecases: Usecases = Depends(get_usecases),
):
    """
    Transcribe audio file to text using STT service.

    This endpoint is used by whatsapp-api-be to transcribe voice messages
    before sending them to the AI for processing. It uses Google Speech
    Recognition as the primary method.
    """
    audio_content = await audio.read()

    audio_format = "ogg"
    if audio.filename and "." in audio.filename:
        audio_format = audio.filename.split(".")[-1].lower()

    result = await usecases.whatsapp.transcribe_audio_usecase.execute(
        audio_bytes=audio_content,
        audio_format=audio_format,
        language=language
    )

    return result


@router.post("/test-send")
async def test_send_message(
    request: Request,
    phone_number: str = Body(..., embed=True),
    message: str = Body(..., embed=True),
    usecases: Usecases = Depends(get_usecases),
):
    """
    Test endpoint for sending WhatsApp messages using Meta Business API.

    This endpoint allows testing the Meta WhatsApp Business API integration.
    """
    try:
        logger.info("Test send request to %s: %s", phone_number, message)

        profile = await _find_active_whatsapp_profile(usecases)
        if profile is None:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "No profile found with active WhatsApp integration",
                },
            )

        test_payload = _build_test_payload(phone_number, message)
        result = await usecases.whatsapp.process_message_usecase.execute(test_payload, profile)

        return {
            "status": "success",
            "message": "Message processed successfully",
            "phone_number": phone_number,
            "result": result,
        }

    except Exception as e:
        logger.error(f"Error testing send: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Error sending message: {str(e)}",
            },
        )


@router.post("/process-external-message", response_model=ProcessExternalMessageResponse)
async def process_external_message(
    req: Request,
    request: ProcessExternalMessageRequest,
    usecases: Usecases = Depends(get_usecases),
) -> ProcessExternalMessageResponse:
    """
    Process a WhatsApp message from whatsapp-api-be service.

    This endpoint receives messages from the Go-based whatsapp-api-be service,
    processes them with AI, and returns the assistant's response.

    The endpoint will:
    1. Find or create a conversation with format: "WhatsApp-{sender}"
    2. Add the user message to the conversation
    3. Get the AI response (auto-generated when conversation is fetched)
    4. Return the AI response to whatsapp-api-be
    """
    try:
        logger.info(
            "Processing external WhatsApp message from %s for user %s",
            request.sender,
            request.user_id,
        )

        conversation_id = await _resolve_external_conversation_id(usecases, request)

        logger.info("Adding user message to conversation %s", conversation_id)

        auth_token = _extract_bearer_token(req)
        if auth_token:
            logger.info("Auth token extracted from request")

        await usecases.conversation.add_message_usecase.execute(
            conversation_id=conversation_id,
            message=MessageInput(content=request.content, context=None),
            sender=SenderEnum.user,
            user_id=request.user_id,
            auth_token=auth_token,
        )

        logger.info("User message added successfully")

        updated_conversation = await usecases.conversation.find_by_id_usecase.execute(conversation_id)

        assistant_response = _extract_last_assistant_response(updated_conversation, conversation_id)

        logger.info(
            f"External message processed successfully for conversation {conversation_id}"
        )

        return ProcessExternalMessageResponse(
            conversation_id=conversation_id,
            assistant_response=assistant_response,
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error processing external message: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/debug")
async def debug_payloads():
    logger.info("Debug payloads request received")

    if not last_payloads:
        return {"message": "No payloads registered"}

    payload_list = list(last_payloads)

    return {"count": len(payload_list), "payloads": payload_list}


@router.post("/webhook")
async def whatsapp_webhook(
    req: Request,
    payload: Dict[Any, Any] = Body(...),
    usecases: Usecases = Depends(get_usecases),
):
    """
    Meta WhatsApp Business API webhook endpoint.

    This endpoint receives webhooks from Meta's WhatsApp Business API,
    processes incoming messages, and responds with AI-generated replies.

    The service supports both Meta Business API and whatsmeow integrations:
    - Meta Business API: Uses this webhook endpoint
    - Whatsmeow: Uses /process-external-message endpoint via whatsapp-api-be
    """
    try:
        timestamp = datetime.now().isoformat()
        sanitized_payload = json.loads(json.dumps(payload))
        last_payloads.append({"timestamp": timestamp, "payload": sanitized_payload})

        logger.info(f"Webhook POST received - object: {payload.get('object')}")

        if payload.get("object") != "whatsapp_business_account":
            logger.warning(
                f"Incorrect payload, received object: {payload.get('object')}"
            )
            return JSONResponse(
                status_code=200,
                content={
                    "status": "ignored",
                    "message": "Payload is not of type whatsapp_business_account",
                },
            )

        if not payload.get("entry") or not payload.get("entry")[0].get("changes"):
            logger.info("Payload contains no changes to process")
            return {
                "status": "success",
                "message": "Payload contains no changes to process",
            }

        business_account_id = _extract_business_account_id(payload)
        logger.info("Business Account ID extracted: %s", business_account_id)

        try:
            profile = await _resolve_webhook_profile(usecases, business_account_id)

            if not profile:
                logger.warning("No profile found with active WhatsApp integration")
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "error",
                        "message": "No profile found with active WhatsApp integration",
                    },
                )

            logger.info(
                "Profile found for business_account_id %s: %s",
                business_account_id,
                profile.id,
            )

            auth_token = _extract_bearer_token(req)
            if auth_token:
                logger.info("Auth token extracted from webhook request")

            result = await usecases.whatsapp.process_message_usecase.execute(payload, profile, auth_token)

            logger.info("Message processed successfully: %s", result)
            return result

        except Exception as e:
            logger.error(
                f"Error searching profile or processing message: {str(e)}", exc_info=True
            )

            return JSONResponse(
                status_code=200,
                content={
                    "status": "error",
                    "message": f"Error processing message: {str(e)}",
                },
            )

    except Exception as e:
        logger.error(f"Unhandled error in webhook: {str(e)}", exc_info=True)

        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": f"General error: {str(e)}"},
        )


@router.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """
    Meta WhatsApp Business API webhook verification endpoint.

    This endpoint handles Meta's webhook verification challenge when setting up
    the WhatsApp Business API integration.
    """
    logger = logging.getLogger(__name__)

    url = str(request.url)
    logger.info(f"Complete URL received: {url}")

    import re

    mode_match = re.search(r"hub\.mode=([^&]+)", url)
    token_match = re.search(r"hub\.verify_token=([^&]+)", url)
    challenge_match = re.search(r"hub\.challenge=([^&]+)", url)

    hub_mode = mode_match.group(1) if mode_match else None
    hub_verify_token = token_match.group(1) if token_match else None
    hub_challenge = challenge_match.group(1) if challenge_match else None

    logger.info(
        f"Webhook verification request received: mode={hub_mode}, token={hub_verify_token}, challenge={hub_challenge}"
    )

    if not hub_mode or not hub_verify_token or not hub_challenge:
        logger.error("Missing parameters in verification request")
        return f"Missing verification parameters: mode={hub_mode}, token={hub_verify_token}, challenge={hub_challenge}"

    verify_token = request.app.state.config_service.whatsapp_config.verify_token
    logger.info(f"Verification token configured: {verify_token}")

    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info(f"Verification successful, returning challenge: {hub_challenge}")

        try:
            challenge_int = int(hub_challenge)
            return PlainTextResponse(content=str(challenge_int))
        except (TypeError, ValueError):
            logger.error(f"Error converting challenge to integer: {hub_challenge}")
            return PlainTextResponse(content=hub_challenge)
    else:
        logger.error(
            f"Verification failed: received token '{hub_verify_token}' does not match expected token '{verify_token}'"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Verification failed: Received token does not match expected token.",
        )
