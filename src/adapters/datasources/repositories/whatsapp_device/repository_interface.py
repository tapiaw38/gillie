from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.domain.whatsapp import WhatsAppDevice


class RepositoryInterface(ABC):
    @abstractmethod
    def create(self, device: WhatsAppDevice) -> str: ...

    @abstractmethod
    def find_by_id(self, device_id: str) -> Optional[WhatsAppDevice]: ...

    @abstractmethod
    def find_by_user_id(self, user_id: str) -> List[WhatsAppDevice]: ...

    @abstractmethod
    def find_by_status(self, status: str) -> List[WhatsAppDevice]: ...

    @abstractmethod
    def update_status(self, device_id: str, status: str, **extra_fields) -> None: ...

    @abstractmethod
    def update_fields(self, device_id: str, **fields) -> None: ...

    @abstractmethod
    def delete(self, device_id: str) -> None: ...
