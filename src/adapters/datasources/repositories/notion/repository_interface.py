from abc import ABC, abstractmethod
from typing import Optional

from src.core.domain.notion import NotionCredentials


class RepositoryInterface(ABC):
    @abstractmethod
    async def save_credentials(self, creds: NotionCredentials) -> None: ...

    @abstractmethod
    async def find_credentials(self) -> Optional[NotionCredentials]: ...
