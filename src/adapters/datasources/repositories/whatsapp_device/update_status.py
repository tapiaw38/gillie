from datetime import datetime, timezone

from pymongo.errors import PyMongoError

from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import WhatsAppDeviceUpdateError


def update_status(client, device_id: str, status: str, **extra_fields) -> None:
    try:
        update = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        update.update(extra_fields)
        client.update_one({"_id": device_id}, {"$set": update})
    except PyMongoError as e:
        raise NewApplicationError(WhatsAppDeviceUpdateError, e)
