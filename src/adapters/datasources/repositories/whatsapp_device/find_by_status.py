from typing import List

from pymongo.errors import PyMongoError

from src.core.domain.whatsapp import WhatsAppDevice
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import WhatsAppDeviceListQueryError


def find_by_status(client, status: str) -> List[WhatsAppDevice]:
    try:
        cursor = client.find({"status": status})
        devices = []
        for doc in cursor:
            doc["id"] = doc.pop("_id")
            devices.append(WhatsAppDevice(**doc))
        return devices
    except PyMongoError as e:
        raise NewApplicationError(WhatsAppDeviceListQueryError, e)
