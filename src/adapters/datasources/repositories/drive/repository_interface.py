from abc import ABC, abstractmethod
from typing import Optional
from src.core.domain.drive import DriveCredentials


class RepositoryInterface(ABC):
    @abstractmethod
    def save_credentials(self, creds: DriveCredentials) -> None: ...

    @abstractmethod
    def find_credentials(self) -> Optional[DriveCredentials]: ...
