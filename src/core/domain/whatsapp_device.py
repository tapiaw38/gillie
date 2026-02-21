from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WhatsAppDevice(BaseModel):
    id: str
    user_id: str
    device_name: str
    phone_number: Optional[str] = None
    status: str = "disconnected"  # disconnected | connecting | connected | authenticated
    qr_code: Optional[str] = None   # base64 PNG data URL
    pair_code: Optional[str] = None
    last_connected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
