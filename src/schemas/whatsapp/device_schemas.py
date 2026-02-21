from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CreateDeviceRequest(BaseModel):
    device_name: str = Field(..., description="Human-readable name for this device", min_length=1)
    phone_number: Optional[str] = Field(None, description="Phone number in international format (optional)")


class AuthenticateDeviceRequest(BaseModel):
    auth_method: str = Field(
        "qr",
        description="Authentication method: 'qr' for QR code scan, 'pair' for phone pair code",
    )
    phone_number: Optional[str] = Field(
        None,
        description="Phone number in international format (required for pair method)",
        examples=["+5491112345678"],
    )


class SendMessageRequest(BaseModel):
    recipient_jid: str = Field(
        ...,
        description="Recipient WhatsApp JID (e.g. '5491112345678@s.whatsapp.net')",
    )
    text: str = Field(..., description="Text message to send", min_length=1)


class SendMessageByPhoneRequest(BaseModel):
    device_id: str = Field(..., description="WhatsApp device ID to send from")
    recipient_phone: str = Field(..., description="Recipient phone number in international format (e.g. '+5491112345678')")
    content: str = Field(..., description="Text message to send", min_length=1)


class DeviceResponse(BaseModel):
    id: str
    user_id: str
    device_name: str
    phone_number: Optional[str] = None
    status: str
    qr_code: Optional[str] = None
    pair_code: Optional[str] = None
    last_connected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DeviceListResponse(BaseModel):
    data: List[DeviceResponse]
    total: int


class AuthenticateResponse(BaseModel):
    auth_method: str
    qr_code: Optional[str] = None
    pair_code: Optional[str] = None


class SendMessageResponse(BaseModel):
    message_id: str
    status: str = "sent"
