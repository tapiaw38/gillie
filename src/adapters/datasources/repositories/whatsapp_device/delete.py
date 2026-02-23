from pymongo.errors import PyMongoError

from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import WhatsAppDeviceDeleteError


def delete(client, device_id: str) -> None:
    try:
        client.delete_one({"_id": device_id})
    except PyMongoError as e:
        raise NewApplicationError(WhatsAppDeviceDeleteError, e)
