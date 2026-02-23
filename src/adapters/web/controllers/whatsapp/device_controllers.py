import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, status

from src.core.use_cases.use_cases import Usecases
from src.schemas.whatsapp.device_schemas import (
    AuthenticateDeviceRequest,
    CreateDeviceRequest,
    DeviceResponse,
    SendMessageByPhoneRequest,
    SendMessageRequest,
    SendMessageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp Device"])

_usecases_instance: Optional[Usecases] = None
_neonize_integration = None


def set_usecases(usecases: Usecases):
    global _usecases_instance
    _usecases_instance = usecases


def set_neonize(neonize_integration):
    global _neonize_integration
    _neonize_integration = neonize_integration


def get_usecases() -> Usecases:
    if _usecases_instance is None:
        raise RuntimeError("Usecases not initialized. Call set_usecases first.")
    return _usecases_instance


def get_neonize():
    if _neonize_integration is None:
        raise RuntimeError("NeonizeIntegration not initialized. Call set_neonize first.")
    return _neonize_integration


def _get_user_id(request: Request) -> str:
    return request.state.user.get("user_id", "default-user")


async def _handle_incoming_message(device_id: str, sender_jid: str, text: str):
    """
    Called by neonize when an incoming WhatsApp message is received.
    Processes the message via AI and replies.
    """
    usecases = get_usecases()
    neonize = get_neonize()

    try:
        device = usecases.whatsapp_device.get_usecase.execute(device_id)
        user_id = device.user_id
        sender_phone = sender_jid.split("@")[0]
        conversation_title = f"WhatsApp-{sender_phone}"
        conversation_id = None

        conversations = usecases.conversation.find_by_user_id_usecase.execute(user_id)
        for conv in conversations.data:
            if conv.title == conversation_title:
                conversation_id = conv.id
                break

        if not conversation_id:
            from src.schemas import ConversationInput
            new_conv = usecases.conversation.create_usecase.execute(
                ConversationInput(title=conversation_title), user_id
            )
            conversation_id = new_conv.data.id

        from src.schemas import MessageInput
        from src.core.domain import SenderEnum

        await usecases.conversation.add_message_usecase.execute(
            conversation_id=conversation_id,
            message=MessageInput(content=text, context=None),
            sender=SenderEnum.user,
            user_id=user_id,
            auth_token=None,
        )

        updated_conv = usecases.conversation.find_by_id_usecase.execute(conversation_id)
        assistant_response = ""
        audio_url = None
        if updated_conv and updated_conv.data.messages:
            assistant_msgs = [m for m in updated_conv.data.messages if m.sender == SenderEnum.assistant]
            if assistant_msgs:
                last = assistant_msgs[-1]
                assistant_response = last.content
                audio_url = getattr(last, "audio_url", None)

        if assistant_response:
            await neonize.send_text(device_id, sender_jid, assistant_response)
            logger.info(f"[device:{device_id}] Replied to {sender_jid}")

            if audio_url:
                sent = await neonize.send_audio(device_id, sender_jid, audio_url)
                if sent:
                    logger.info(f"[device:{device_id}] Sent audio to {sender_jid}")
                else:
                    logger.warning(f"[device:{device_id}] Audio send failed")

    except Exception as e:
        logger.error(
            f"[device:{device_id}] Error handling incoming message from {sender_jid}: {e}",
            exc_info=True,
        )


@router.post("/device/register", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(request: Request, body: CreateDeviceRequest):
    user_id = _get_user_id(request)
    usecases = get_usecases()
    device = usecases.whatsapp_device.create_usecase.execute(
        user_id=user_id,
        device_name=body.device_name,
        phone_number=body.phone_number,
    )
    return DeviceResponse(**device.dict())


@router.get("/device", response_model=List[DeviceResponse])
async def list_devices(request: Request):
    user_id = _get_user_id(request)
    usecases = get_usecases()
    devices = usecases.whatsapp_device.list_usecase.execute(user_id)
    return [DeviceResponse(**d.dict()) for d in devices]


@router.get("/device/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str):
    usecases = get_usecases()
    device = usecases.whatsapp_device.get_usecase.execute(device_id)
    return DeviceResponse(**device.dict())


@router.delete("/device/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: str):
    usecases = get_usecases()
    neonize = get_neonize()
    await usecases.whatsapp_device.delete_usecase.execute(device_id, neonize)


@router.post("/device/{device_id}/authenticate", response_model=DeviceResponse)
async def authenticate_device(device_id: str, body: AuthenticateDeviceRequest):
    usecases = get_usecases()
    neonize = get_neonize()
    await usecases.whatsapp_device.authenticate_usecase.execute(
        device_id=device_id,
        auth_method=body.auth_method,
        neonize_integration=neonize,
        phone_number=body.phone_number,
        message_handler=_handle_incoming_message,
    )
    device = usecases.whatsapp_device.get_usecase.execute(device_id)
    return DeviceResponse(**device.dict())


@router.post("/device/{device_id}/connect", status_code=status.HTTP_204_NO_CONTENT)
async def connect_device(device_id: str):
    usecases = get_usecases()
    neonize = get_neonize()
    await usecases.whatsapp_device.connect_usecase.execute(
        device_id=device_id,
        neonize_integration=neonize,
        message_handler=_handle_incoming_message,
    )


@router.post("/device/{device_id}/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_device(device_id: str):
    usecases = get_usecases()
    neonize = get_neonize()
    await usecases.whatsapp_device.disconnect_usecase.execute(device_id, neonize)


@router.post("/device/{device_id}/send", response_model=SendMessageResponse)
async def send_message(device_id: str, body: SendMessageRequest):
    usecases = get_usecases()
    neonize = get_neonize()
    message_id = await usecases.whatsapp_device.send_message_usecase.execute(
        device_id=device_id,
        recipient_jid=body.recipient_jid,
        text=body.text,
        neonize_integration=neonize,
    )
    return SendMessageResponse(message_id=message_id)


@router.post("/message/send", response_model=SendMessageResponse)
async def send_message_by_phone(body: SendMessageByPhoneRequest):
    """
    UI-compatible send endpoint.
    Accepts { device_id, recipient_phone, content } and converts phone → JID.
    """
    usecases = get_usecases()
    neonize = get_neonize()

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
        usecases = get_usecases()
        interval = 2

        for i in range(60):
            device = usecases.whatsapp_device.get_usecase.execute(device_id)
            logger.info(f"[device:{device_id}] qr-stream poll {i+1}/60 — status={device.status} qr_code={'SET' if device.qr_code else 'NONE'}")

            if device.status == "authenticated":
                await websocket.send_json({"type": "authenticated"})
                return

            if device.qr_code:
                await websocket.send_json({"type": "qr", "data": device.qr_code})
                break

            await asyncio.sleep(interval)

        for i in range(60):
            device = usecases.whatsapp_device.get_usecase.execute(device_id)
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
