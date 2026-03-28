from abc import ABC, abstractmethod
from typing import Optional

from src.core.domain.gmail import GmailSession, GmailCredentials


class RepositoryInterface(ABC):
    @abstractmethod
    def upsert_session(self, session: GmailSession) -> str: ...

    @abstractmethod
    def find_active_session(self, user_id: str) -> Optional[GmailSession]: ...

    @abstractmethod
    def deactivate_session(self, user_id: str) -> None: ...

    @abstractmethod
    def save_credentials(self, creds: GmailCredentials) -> None: ...

    @abstractmethod
    def find_credentials(self) -> Optional[GmailCredentials]: ...
