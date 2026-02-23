from typing import List, Optional

from src.adapters.datasources.datasources import Datasources
from src.core.domain.whatsapp import WhatsAppDevice
from .repository_interface import RepositoryInterface
from .create import create
from .find_by_id import find_by_id
from .find_by_user_id import find_by_user_id
from .find_by_status import find_by_status
from .update_status import update_status
from .update_fields import update_fields
from .delete import delete


class Repository(RepositoryInterface):
    def __init__(self, datasources: Datasources):
        self.client = datasources.no_sql_whatsapp_devices_client
        self.client.create_index("user_id")

    def create(self, device: WhatsAppDevice) -> str:
        return create(self.client, device)

    def find_by_id(self, device_id: str) -> Optional[WhatsAppDevice]:
        return find_by_id(self.client, device_id)

    def find_by_user_id(self, user_id: str) -> List[WhatsAppDevice]:
        return find_by_user_id(self.client, user_id)

    def find_by_status(self, status: str) -> List[WhatsAppDevice]:
        return find_by_status(self.client, status)

    def update_status(self, device_id: str, status: str, **extra_fields) -> None:
        update_status(self.client, device_id, status, **extra_fields)

    def update_fields(self, device_id: str, **fields) -> None:
        update_fields(self.client, device_id, **fields)

    def delete(self, device_id: str) -> None:
        delete(self.client, device_id)
