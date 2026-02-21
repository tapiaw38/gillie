from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime
from src.core.domain.calendar import CalendarSession, CalendarEvent


class RepositoryInterface(ABC):
    @abstractmethod
    def upsert_session(self, session: CalendarSession) -> str: ...

    @abstractmethod
    def find_active_session(self, user_id: str) -> Optional[CalendarSession]: ...

    @abstractmethod
    def deactivate_session(self, user_id: str) -> None: ...

    @abstractmethod
    def create_event(self, event: CalendarEvent) -> str: ...

    @abstractmethod
    def find_event_by_id(self, event_id: str, user_id: str) -> Optional[CalendarEvent]: ...

    @abstractmethod
    def find_event_by_google_id(self, google_id: str, user_id: str) -> Optional[CalendarEvent]: ...

    @abstractmethod
    def find_events_by_user(
        self, user_id: str, start: Optional[datetime], end: Optional[datetime], limit: int
    ) -> List[CalendarEvent]: ...

    @abstractmethod
    def update_event(self, event: CalendarEvent) -> None: ...

    @abstractmethod
    def delete_event(self, event_id: str, user_id: str) -> None: ...
