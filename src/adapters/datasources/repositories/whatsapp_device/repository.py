import logging
from typing import List, Optional
from datetime import datetime, timezone
from pymongo.errors import PyMongoError

from src.core.domain.whatsapp_device import WhatsAppDevice
from src.adapters.datasources.datasources import Datasources
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import (
    WhatsAppDeviceCreateError,
    WhatsAppDeviceGetQueryError,
    WhatsAppDeviceListQueryError,
    WhatsAppDeviceDeleteError,
    WhatsAppDeviceUpdateError,
)

logger = logging.getLogger(__name__)


class Repository:
    def __init__(self, datasources: Datasources):
        self.client = datasources.no_sql_whatsapp_devices_client
        self.client.create_index("user_id")
        self.client.create_index("id", unique=True)

    def create(self, device: WhatsAppDevice) -> str:
        try:
            doc = device.dict()
            doc["_id"] = device.id
            self.client.insert_one(doc)
            return device.id
        except PyMongoError as e:
            raise NewApplicationError(WhatsAppDeviceCreateError, e)

    def find_by_id(self, device_id: str) -> Optional[WhatsAppDevice]:
        try:
            doc = self.client.find_one({"_id": device_id})
            if not doc:
                return None
            doc["id"] = doc.pop("_id")
            return WhatsAppDevice(**doc)
        except PyMongoError as e:
            raise NewApplicationError(WhatsAppDeviceGetQueryError, e)

    def find_by_user_id(self, user_id: str) -> List[WhatsAppDevice]:
        try:
            cursor = self.client.find({"user_id": user_id})
            devices = []
            for doc in cursor:
                doc["id"] = doc.pop("_id")
                devices.append(WhatsAppDevice(**doc))
            return devices
        except PyMongoError as e:
            raise NewApplicationError(WhatsAppDeviceListQueryError, e)

    def find_by_status(self, status: str) -> List[WhatsAppDevice]:
        try:
            cursor = self.client.find({"status": status})
            devices = []
            for doc in cursor:
                doc["id"] = doc.pop("_id")
                devices.append(WhatsAppDevice(**doc))
            return devices
        except PyMongoError as e:
            raise NewApplicationError(WhatsAppDeviceListQueryError, e)

    def update_status(self, device_id: str, status: str, **extra_fields) -> None:
        try:
            update = {
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }
            update.update(extra_fields)
            self.client.update_one({"_id": device_id}, {"$set": update})
        except PyMongoError as e:
            raise NewApplicationError(WhatsAppDeviceUpdateError, e)

    def update_fields(self, device_id: str, **fields) -> None:
        try:
            fields["updated_at"] = datetime.now(timezone.utc)
            self.client.update_one({"_id": device_id}, {"$set": fields})
        except PyMongoError as e:
            raise NewApplicationError(WhatsAppDeviceUpdateError, e)

    def delete(self, device_id: str) -> None:
        try:
            self.client.delete_one({"_id": device_id})
        except PyMongoError as e:
            raise NewApplicationError(WhatsAppDeviceDeleteError, e)
