from typing import List, Optional

from src.adapters.datasources.datasources import Datasources
from src.core.domain.whatsapp import WhatsAppDevice
from pymongo.errors import PyMongoError
from datetime import datetime, timezone

from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.whatsapp_device import (
    WhatsAppDeviceCreateError,
    WhatsAppDeviceDeleteError,
    WhatsAppDeviceGetQueryError,
    WhatsAppDeviceListQueryError,
    WhatsAppDeviceUpdateError,
)
from .repository_interface import RepositoryInterface


class Repository(RepositoryInterface):
    def __init__(self, datasources: Datasources):
        self.client = datasources.no_sql_whatsapp_devices_client
 
    async def ensure_indexes(self) -> None:
        await self.client.create_index("user_id")

    async def create(self, device: WhatsAppDevice) -> str:
        try:
            doc = device.dict()
            doc["_id"] = device.id
            await self.client.insert_one(doc)
            return device.id
        except PyMongoError as exc:
            raise NewApplicationError(WhatsAppDeviceCreateError, exc)

    async def find_by_id(self, device_id: str) -> Optional[WhatsAppDevice]:
        try:
            doc = await self.client.find_one({"_id": device_id})
            if not doc:
                return None
            doc["id"] = doc.pop("_id")
            return WhatsAppDevice(**doc)
        except PyMongoError as exc:
            raise NewApplicationError(WhatsAppDeviceGetQueryError, exc)

    async def find_by_user_id(self, user_id: str) -> List[WhatsAppDevice]:
        try:
            cursor = self.client.find({"user_id": user_id})
            devices = []
            for doc in await cursor.to_list(length=None):
                doc["id"] = doc.pop("_id")
                devices.append(WhatsAppDevice(**doc))
            return devices
        except PyMongoError as exc:
            raise NewApplicationError(WhatsAppDeviceListQueryError, exc)

    async def find_by_status(self, status: str) -> List[WhatsAppDevice]:
        try:
            cursor = self.client.find({"status": status})
            devices = []
            for doc in await cursor.to_list(length=None):
                doc["id"] = doc.pop("_id")
                devices.append(WhatsAppDevice(**doc))
            return devices
        except PyMongoError as exc:
            raise NewApplicationError(WhatsAppDeviceListQueryError, exc)

    async def update_status(self, device_id: str, status: str, **extra_fields) -> None:
        try:
            update = {
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }
            update.update(extra_fields)
            await self.client.update_one({"_id": device_id}, {"$set": update})
        except PyMongoError as exc:
            raise NewApplicationError(WhatsAppDeviceUpdateError, exc)

    async def update_fields(self, device_id: str, **fields) -> None:
        try:
            fields["updated_at"] = datetime.now(timezone.utc)
            await self.client.update_one({"_id": device_id}, {"$set": fields})
        except PyMongoError as exc:
            raise NewApplicationError(WhatsAppDeviceUpdateError, exc)

    async def delete(self, device_id: str) -> None:
        try:
            await self.client.delete_one({"_id": device_id})
        except PyMongoError as exc:
            raise NewApplicationError(WhatsAppDeviceDeleteError, exc)
