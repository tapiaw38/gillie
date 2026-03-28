from abc import ABC, abstractmethod
from typing import Optional
from src.core.domain.calendar import CalendarSession, CalendarCredentials


class RepositoryInterface(ABC):
    @abstractmethod
    def upsert_session(self, session: CalendarSession) -> str: ...

    @abstractmethod
    def find_active_session(self, user_id: str) -> Optional[CalendarSession]: ...

    @abstractmethod
    def deactivate_session(self, user_id: str) -> None: ...

    @abstractmethod
    def save_credentials(self, creds: CalendarCredentials) -> None: ...

    @abstractmethod
    def find_credentials(self) -> Optional[CalendarCredentials]: ...
