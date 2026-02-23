from pymongo.errors import PyMongoError

from src.core.domain.whatsapp import WhatsAppDevice
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import WhatsAppDeviceCreateError


def create(client, device: WhatsAppDevice) -> str:
    try:
        doc = device.dict()
        doc["_id"] = device.id
        client.insert_one(doc)
        return device.id
    except PyMongoError as e:
        raise NewApplicationError(WhatsAppDeviceCreateError, e)
