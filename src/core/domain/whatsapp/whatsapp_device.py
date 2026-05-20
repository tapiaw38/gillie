from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class WhatsAppDevicePolicies(BaseModel):
    allowed_numbers: List[str] = Field(default_factory=list)
    blocked_numbers: List[str] = Field(default_factory=list)
    incoming_filter_mode: str = "off"  # off | whitelist | blacklist | both
    outgoing_filter_mode: str = "off"  # off | whitelist | blacklist | both

    @staticmethod
    def normalize_contact(value: str) -> str:
        if not value:
            return ""
        base = value.split("@")[0].strip()
        return "".join(ch for ch in base if ch.isdigit())

    @classmethod
    def normalized_list(cls, values: List[str]) -> List[str]:
        normalized = []
        seen = set()
        for value in values or []:
            phone = cls.normalize_contact(value)
            if phone and phone not in seen:
                seen.add(phone)
                normalized.append(phone)
        return normalized

    def contact_allowed(self, contact: str, direction: str = "incoming") -> bool:
        phone = self.normalize_contact(contact)
        mode = self.incoming_filter_mode if direction == "incoming" else self.outgoing_filter_mode
        blocked = set(self.normalized_list(self.blocked_numbers))
        allowed = set(self.normalized_list(self.allowed_numbers))

        if phone and phone in blocked:
            return False
        if mode == "off":
            return True
        if mode == "blacklist":
            return True
        if mode == "whitelist":
            return phone in allowed
        if mode == "both":
            return phone in allowed
        return True

    def contact_allowed_any(self, contacts: List[str], direction: str = "incoming") -> bool:
        normalized_contacts = self.normalized_list(contacts)
        mode = self.incoming_filter_mode if direction == "incoming" else self.outgoing_filter_mode
        blocked = set(self.normalized_list(self.blocked_numbers))
        allowed = set(self.normalized_list(self.allowed_numbers))

        if any(contact in blocked for contact in normalized_contacts):
            return False
        if mode == "off":
            return True
        if mode == "blacklist":
            return True
        if mode in ("whitelist", "both"):
            return any(contact in allowed for contact in normalized_contacts)
        return True


class WhatsAppDevice(BaseModel):
    id: str
    user_id: str
    device_name: str
    phone_number: Optional[str] = None
    device_policies: WhatsAppDevicePolicies = Field(default_factory=WhatsAppDevicePolicies)
    status: str = "disconnected"  # disconnected | connecting | connected | authenticated
    qr_code: Optional[str] = None   # base64 PNG data URL
    pair_code: Optional[str] = None
    last_connected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
