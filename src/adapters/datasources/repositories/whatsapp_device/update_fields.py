from datetime import datetime, timezone

from pymongo.errors import PyMongoError

from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import WhatsAppDeviceUpdateError


def update_fields(client, device_id: str, **fields) -> None:
    try:
        fields["updated_at"] = datetime.now(timezone.utc)
        client.update_one({"_id": device_id}, {"$set": fields})
    except PyMongoError as e:
        raise NewApplicationError(WhatsAppDeviceUpdateError, e)
