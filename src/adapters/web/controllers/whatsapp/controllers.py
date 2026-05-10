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

last_payloads = deque(maxlen=10)

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])


@router.get("/verify", response_class=PlainTextResponse)
async def verify_endpoint():
    logger = logging.getLogger(__name__)
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
    logger = logging.getLogger(__name__)
    try:
        logger.info(f"Test send request to {phone_number}: {message}")

        profile = await usecases.profile.find_with_active_whatsapp_integration_usecase.execute()

        if not profile:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "No profile found with active WhatsApp integration",
                },
            )

        whatsapp_integration = None
        for integration in profile.integrations:
            if integration.name == "whatsapp" and integration.activated:
                whatsapp_integration = integration
                break

        if not whatsapp_integration:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "No active WhatsApp integration found in the profile",
                },
            )

        test_payload = {
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
    logger = logging.getLogger(__name__)

    try:
        logger.info(
            f"Processing external WhatsApp message from {request.sender} for user {request.user_id}"
        )

        conversation_title = f"WhatsApp-{request.sender}"

        conversation_id = None

        if request.conversation_id:
            # Verify the conversation exists
            try:
                conversation = await usecases.conversation.find_by_id_usecase.execute(request.conversation_id)
                conversation_id = request.conversation_id
                logger.info(
                    f"Using existing conversation: {conversation_id}"
                )
            except HTTPException as e:
                if e.status_code == 404:
                    logger.warning(
                        f"Conversation {request.conversation_id} not found, will create new one"
                    )
                else:
                    raise

        if not conversation_id:
            conversation_list = await usecases.conversation.find_by_user_id_usecase.execute(request.user_id)

            for conversation_data in conversation_list.data:
                if conversation_title == conversation_data.title:
                    conversation_id = conversation_data.id
                    logger.info(
                        f"Found existing conversation by title: {conversation_id}"
                    )
                    break

        if not conversation_id:
            logger.info(f"Creating new conversation: {conversation_title}")

            conversation_input = ConversationInput(
                title=conversation_title
            )

            new_conversation = await usecases.conversation.create_usecase.execute(conversation_input, request.user_id)

            conversation_id = new_conversation.data.id
            logger.info(f"Created new conversation: {conversation_id}")

        logger.info(f"Adding user message to conversation {conversation_id}")

        auth_token = None
        auth_header = req.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            auth_token = auth_header.replace("Bearer ", "")
            logger.info("Auth token extracted from request")

        message_input = MessageInput(content=request.content, context=None)

        await usecases.conversation.add_message_usecase.execute(
            conversation_id=conversation_id,
            message=message_input,
            sender=SenderEnum.user,
            user_id=request.user_id,
            auth_token=auth_token,
        )

        logger.info("User message added successfully")

        updated_conversation = await usecases.conversation.find_by_id_usecase.execute(conversation_id)

        assistant_response = ""

        if updated_conversation and updated_conversation.data.messages:
            assistant_messages = [
                msg
                for msg in updated_conversation.data.messages
                if msg.sender == SenderEnum.assistant
            ]

            if assistant_messages:
                last_assistant_message = assistant_messages[-1]
                assistant_response = last_assistant_message.content
                logger.info(
                    f"AI response generated: {assistant_response[:100]}..."
                    if len(assistant_response) > 100
                    else f"AI response generated: {assistant_response}"
                )
            else:
                logger.warning(
                    f"No assistant messages found in conversation {conversation_id}"
                )
                assistant_response = "I apologize, but I couldn't generate a response at this moment."
        else:
            logger.error(
                f"Could not retrieve updated conversation {conversation_id}"
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve conversation after processing message"
            )

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
    logger = logging.getLogger(__name__)
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
    logger = logging.getLogger(__name__)
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

        business_account_id = None
        try:
            logger.debug(f"Estructura del payload: {payload}")

            if "entry" in payload and len(payload["entry"]) > 0:
                entry = payload["entry"][0]
                logger.debug(f"Entry encontrado: {entry}")

                if "changes" in entry and len(entry["changes"]) > 0:
                    value = entry["changes"][0]["value"]
                    logger.debug(f"Value encontrado: {value}")

                    if (
                        "metadata" in value
                        and "business_account_id" in value["metadata"]
                    ):
                        business_account_id = value["metadata"]["business_account_id"]
                    elif "metadata" in value and "phone_number_id" in value["metadata"]:
                        business_account_id = value["metadata"]["phone_number_id"]
                    elif "phone_number_id" in value:
                        business_account_id = value["phone_number_id"]

            if not business_account_id and "phone_number_id" in payload:
                business_account_id = payload["phone_number_id"]

            if not business_account_id:

                def search_for_id(
                    obj, keys=["business_account_id", "phone_number_id", "from_id"]
                ):
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

                business_account_id = search_for_id(payload)

            if business_account_id:
                logger.info(f"Business Account ID extracted: {business_account_id}")
            else:
                logger.warning(
                    "Could not find business ID, using 'default' for debugging"
                )
                business_account_id = "default"

        except (KeyError, IndexError) as e:
            logger.error(f"Error al obtener business_account_id: {str(e)}")
            logger.debug(f"Payload structure: {payload}")

            business_account_id = "default"
            logger.info("Using business_account_id 'default' for debugging")

        try:
            if business_account_id == "default":
                logger.info(
                    "Looking for a profile with any active WhatsApp integration"
                )
                profile = await run_in_threadpool(
                    usecases.profile.find_with_active_whatsapp_integration_usecase.execute,
                )
            else:
                profile = await run_in_threadpool(
                    usecases.profile.find_by_whatsapp_business_id_usecase.execute,
                    business_account_id,
                )

            if not profile:
                if business_account_id != "default":
                    logger.warning(
                        f"No profile found with business_account_id: {business_account_id}, searching for profiles with active WhatsApp"
                    )
                    profile = await run_in_threadpool(
                        usecases.profile.find_with_active_whatsapp_integration_usecase.execute,
                    )

                if not profile:
                    logger.warning(
                        "No profile found with active WhatsApp integration"
                    )
                    return JSONResponse(
                        status_code=200,
                        content={
                            "status": "error",
                            "message": "No profile found with active WhatsApp integration",
                        },
                    )

            logger.info(
                f"Profile found for business_account_id {business_account_id}: {profile.id}"
            )

            # Extract auth token from request headers
            auth_token = None
            auth_header = req.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                auth_token = auth_header.replace("Bearer ", "")
                logger.info("Auth token extracted from webhook request")

            result = await usecases.whatsapp.process_message_usecase.execute(payload, profile, auth_token)

            logger.info(f"Message processed successfully: {result}")
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

    from src.core.platform.config.service import get_config_service
    config = get_config_service()
    verify_token = config.whatsapp_config.verify_token
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
