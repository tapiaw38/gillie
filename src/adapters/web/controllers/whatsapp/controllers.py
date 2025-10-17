from fastapi import APIRouter, Depends, Body, HTTPException, status, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from src.adapters.services.services import Services
from src.adapters.services.whatsapp.service import WhatsAppService
from src.adapters.services.profile.service import ProfileService
from typing import Dict, Any, List, Deque
import logging
import os
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


@router.post("/test-send")
async def test_send_message(
    phone_number: str = Body(..., embed=True),
    message: str = Body(..., embed=True),
    services: Services = Depends(Services.get_instance),
):
    logger = logging.getLogger(__name__)
    try:
        logger.info(f"Test send request to {phone_number}: {message}")

        profile = await services.profile.find_with_active_whatsapp_integration()

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

        result = await services.whatsapp.process_message(test_payload, profile)

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
    payload: Dict[Any, Any] = Body(...),
    services: Services = Depends(Services.get_instance),
):
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
                profile = await services.profile.find_with_active_whatsapp_integration()
            else:
                profile = await services.profile.find_by_whatsapp_business_id(
                    business_account_id
                )

            if not profile:
                if business_account_id != "default":
                    logger.warning(
                        f"No profile found with business_account_id: {business_account_id}, searching for profiles with active WhatsApp"
                    )
                    profile = (
                        await services.profile.find_with_active_whatsapp_integration()
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

            result = await services.whatsapp.process_message(payload, profile)

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
