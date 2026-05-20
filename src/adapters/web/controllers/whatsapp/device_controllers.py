import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, status

from src.core.use_cases.use_cases import Usecases
from src.adapters.web.dependencies import get_usecases
from src.schemas.whatsapp.device_schemas import (
    AuthenticateDeviceRequest,
    CreateDeviceRequest,
    DeviceResponse,
    SendMessageByPhoneRequest,
    SendMessageRequest,
    SendMessageResponse,
    UpdateDevicePoliciesRequest,
)
from src.core.domain.whatsapp import WhatsAppDevicePolicies

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp Device"])


def set_app(app):
    router.app = app


def _get_app():
    app = getattr(router, "app", None)
    if app is None:
        raise RuntimeError("FastAPI app not initialized. Call set_app first.")
    return app


def _get_neonize_from_app(app):
    neonize = getattr(app.state, "neonize_integration", None)
    if neonize is None:
        raise RuntimeError("NeonizeIntegration not initialized. Call set_neonize first.")
    return neonize


def _get_user_id(request: Request) -> str:
    return request.state.user.get("user_id", "default-user")


async def _handle_incoming_message(
    device_id: str,
    sender_jid: str,
    text: str,
    reply_jid: Optional[str] = None,
    sender_candidates: Optional[List[str]] = None,
):
    """
    Called by neonize when an incoming WhatsApp message is received.
    Processes the message via AI and replies.
    """
    app = _get_app()
    usecases = app.state.usecases
    neonize = _get_neonize_from_app(app)
    send_target = reply_jid or sender_jid

    try:
        device = await usecases.whatsapp_device.get_usecase.execute(device_id)
        user_id = device.user_id
        sender_phone = sender_jid.split("@")[0]
        candidate_contacts = sender_candidates or [sender_jid]
        conversation_title = f"WhatsApp-{sender_phone}"
        if not device.device_policies.contact_allowed_any(candidate_contacts, "incoming"):
            logger.info(
                f"[device:{device_id}] Blocked incoming message from {sender_jid} "
                f"(candidates={candidate_contacts}) by device policies"
            )
            return
        conversation_id = None

        conversations = await usecases.conversation.find_by_user_id_usecase.execute(user_id)
        for conv in conversations.data:
            if conv.title == conversation_title:
                conversation_id = conv.id
                break

        if not conversation_id:
            from src.schemas import ConversationInput
            new_conv = await usecases.conversation.create_usecase.execute(
                ConversationInput(title=conversation_title),
                user_id,
            )
            conversation_id = new_conv.data.id

        from src.schemas import MessageInput
        from src.core.domain import SenderEnum

        await usecases.conversation.add_message_usecase.execute(
            conversation_id=conversation_id,
            message=MessageInput(
                content=text,
                context=(
                    "[CANAL: whatsapp] El usuario está chateando por WhatsApp. "
                    "Si el usuario pide una captura de pantalla o imagen de la pantalla, usa send_screenshot. "
                    "Si el usuario pide recibir un archivo, usa send_file."
                ),
            ),
            sender=SenderEnum.user,
            user_id=user_id,
            auth_token=None,
        )

        updated_conv = await usecases.conversation.find_by_id_usecase.execute(conversation_id)
        new_assistant_msgs = []
        if updated_conv and updated_conv.data.messages:
            all_msgs = updated_conv.data.messages
            last_user_idx = next(
                (i for i in range(len(all_msgs) - 1, -1, -1)
                 if all_msgs[i].sender != SenderEnum.assistant),
                None
            )
            if last_user_idx is not None:
                new_assistant_msgs = [
                    m for m in all_msgs[last_user_idx + 1:]
                    if m.sender == SenderEnum.assistant
                ]

        if not device.device_policies.contact_allowed_any(candidate_contacts, "outgoing"):
            logger.info(
                f"[device:{device_id}] Blocked outgoing reply to {send_target} "
                f"(candidates={candidate_contacts}) by device policies"
            )
            return

        from src.core.platform.utils.message_parser import parse_message_segments

        for msg in new_assistant_msgs:
            for segment in parse_message_segments(msg.content):
                if segment["type"] == "image":
                    await neonize.send_image(device_id, send_target, segment["content"])
                elif segment["type"] == "document":
                    await neonize.send_document(device_id, send_target, segment["content"])
                elif segment["content"]:
                    await neonize.send_text(device_id, send_target, segment["content"])
            logger.info(f"[device:{device_id}] Replied to {sender_jid}")

        if new_assistant_msgs:
            audio_url = getattr(new_assistant_msgs[-1], "audio_url", None)
            if audio_url:
                sent = await neonize.send_audio(device_id, send_target, audio_url)
                if sent:
                    logger.info(f"[device:{device_id}] Sent audio to {send_target}")
                else:
                    logger.warning(f"[device:{device_id}] Audio send failed to {send_target}")

    except Exception as e:
        logger.error(
            f"[device:{device_id}] Error handling incoming message from {sender_jid}: {e}",
            exc_info=True,
        )


@router.post("/device/register", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(request: Request, body: CreateDeviceRequest, usecases: Usecases = Depends(get_usecases)):
    user_id = _get_user_id(request)
    device = await usecases.whatsapp_device.create_usecase.execute(
        user_id,
        body.device_name,
        body.phone_number,
        WhatsAppDevicePolicies(**body.device_policies.dict()),
    )
    return DeviceResponse(**device.dict())


@router.get("/device", response_model=List[DeviceResponse])
async def list_devices(request: Request, usecases: Usecases = Depends(get_usecases)):
    user_id = _get_user_id(request)
    devices = await usecases.whatsapp_device.list_usecase.execute(user_id)
    return [DeviceResponse(**d.dict()) for d in devices]


@router.get("/device/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str, request: Request, usecases: Usecases = Depends(get_usecases)):
    device = await usecases.whatsapp_device.get_usecase.execute(device_id)
    return DeviceResponse(**device.dict())


@router.patch("/device/{device_id}/policies", response_model=DeviceResponse)
async def update_device_policies_patch(
    device_id: str,
    body: UpdateDevicePoliciesRequest,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = _get_user_id(request)
    device = await usecases.whatsapp_device.update_policies_usecase.execute(
        device_id,
        WhatsAppDevicePolicies(**body.device_policies.dict()),
        user_id,
    )
    return DeviceResponse(**device.dict())


@router.post("/device/{device_id}/policies", response_model=DeviceResponse)
async def update_device_policies_post(
    device_id: str,
    body: UpdateDevicePoliciesRequest,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = _get_user_id(request)
    device = await usecases.whatsapp_device.update_policies_usecase.execute(
        device_id,
        WhatsAppDevicePolicies(**body.device_policies.dict()),
        user_id,
    )
    return DeviceResponse(**device.dict())


@router.delete("/device/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: str, request: Request, usecases: Usecases = Depends(get_usecases)):
    neonize = _get_neonize_from_app(request.app)
    await usecases.whatsapp_device.delete_usecase.execute(device_id, neonize)


@router.post("/device/{device_id}/authenticate", response_model=DeviceResponse)
async def authenticate_device(device_id: str, body: AuthenticateDeviceRequest, request: Request, usecases: Usecases = Depends(get_usecases)):
    neonize = _get_neonize_from_app(request.app)
    await usecases.whatsapp_device.authenticate_usecase.execute(
        device_id=device_id,
        auth_method=body.auth_method,
        neonize_integration=neonize,
        phone_number=body.phone_number,
        message_handler=_handle_incoming_message,
    )
    device = await usecases.whatsapp_device.get_usecase.execute(device_id)
    return DeviceResponse(**device.dict())


@router.post("/device/{device_id}/connect", status_code=status.HTTP_204_NO_CONTENT)
async def connect_device(device_id: str, request: Request, usecases: Usecases = Depends(get_usecases)):
    neonize = _get_neonize_from_app(request.app)
    await usecases.whatsapp_device.connect_usecase.execute(
        device_id=device_id,
        neonize_integration=neonize,
        message_handler=_handle_incoming_message,
    )


@router.post("/device/{device_id}/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_device(device_id: str, request: Request, usecases: Usecases = Depends(get_usecases)):
    neonize = _get_neonize_from_app(request.app)
    await usecases.whatsapp_device.disconnect_usecase.execute(device_id, neonize)


@router.post("/device/{device_id}/send", response_model=SendMessageResponse)
async def send_message(device_id: str, body: SendMessageRequest, request: Request, usecases: Usecases = Depends(get_usecases)):
    neonize = _get_neonize_from_app(request.app)
    message_id = await usecases.whatsapp_device.send_message_usecase.execute(
        device_id=device_id,
        recipient_jid=body.recipient_jid,
        text=body.text,
        neonize_integration=neonize,
    )
    return SendMessageResponse(message_id=message_id)


@router.post("/message/send", response_model=SendMessageResponse)
async def send_message_by_phone(body: SendMessageByPhoneRequest, request: Request, usecases: Usecases = Depends(get_usecases)):
    """
    UI-compatible send endpoint.
    Accepts { device_id, recipient_phone, content } and converts phone → JID.
    """
    neonize = _get_neonize_from_app(request.app)

    phone = body.recipient_phone.lstrip("+")
    recipient_jid = f"{phone}@s.whatsapp.net"

    message_id = await usecases.whatsapp_device.send_message_usecase.execute(
        device_id=body.device_id,
        recipient_jid=recipient_jid,
        text=body.content,
        neonize_integration=neonize,
    )
    return SendMessageResponse(message_id=message_id)


@router.websocket("/device/{device_id}/qr-stream")
async def qr_stream(websocket: WebSocket, device_id: str):
    """
    WebSocket that pushes QR code as base64 PNG once ready,
    then sends {"type": "authenticated"} when the user scans it.
    """
    await websocket.accept()

    try:
        usecases = websocket.app.state.usecases
        interval = 2

        for i in range(60):
            device = await usecases.whatsapp_device.get_usecase.execute(device_id)
            logger.info(f"[device:{device_id}] qr-stream poll {i+1}/60 — status={device.status} qr_code={'SET' if device.qr_code else 'NONE'}")

            if device.status == "authenticated":
                await websocket.send_json({"type": "authenticated"})
                return

            if device.qr_code:
                await websocket.send_json({"type": "qr", "data": device.qr_code})
                break

            await asyncio.sleep(interval)

        for i in range(60):
            device = await usecases.whatsapp_device.get_usecase.execute(device_id)
            logger.info(f"[device:{device_id}] qr-stream auth-poll {i+1}/60 — status={device.status}")
            if device.status == "authenticated":
                await websocket.send_json({"type": "authenticated"})
                break
            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        logger.info(f"[device:{device_id}] QR stream WebSocket disconnected")
    except Exception as e:
        logger.error(f"[device:{device_id}] QR stream error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
