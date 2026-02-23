from typing import Optional

from pymongo.errors import PyMongoError

from src.core.domain.whatsapp import WhatsAppDevice
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import WhatsAppDeviceGetQueryError


def find_by_id(client, device_id: str) -> Optional[WhatsAppDevice]:
    try:
        doc = client.find_one({"_id": device_id})
        if not doc:
            return None
        doc["id"] = doc.pop("_id")
        return WhatsAppDevice(**doc)
    except PyMongoError as e:
        raise NewApplicationError(WhatsAppDeviceGetQueryError, e)
