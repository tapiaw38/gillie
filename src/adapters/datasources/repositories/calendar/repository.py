from typing import Optional, List
from datetime import datetime
from src.core.domain.calendar import CalendarSession, CalendarEvent
from src.adapters.datasources.datasources import Datasources
from .repository_interface import RepositoryInterface
from .create_session import create_session
from .find_session import find_active_session
from .upsert_session import upsert_session, deactivate_session
from .create_event import create_event
from .find_event import find_event_by_id, find_event_by_google_id
from .find_events import find_events_by_user
from .update_event import update_event
from .delete_event import delete_event


class Repository(RepositoryInterface):
    def __init__(self, datasources: Datasources):
        self.sessions_client = datasources.no_sql_calendar_sessions_client
        self.events_client = datasources.no_sql_calendar_events_client
        self.sessions_client.create_index("user_id")
        self.events_client.create_index("user_id")
        self.events_client.create_index("google_id")
        self.events_client.create_index("start_time")

    def upsert_session(self, session: CalendarSession) -> str:
        return upsert_session(self.sessions_client, session)

    def find_active_session(self, user_id: str) -> Optional[CalendarSession]:
        return find_active_session(self.sessions_client, user_id)

    def deactivate_session(self, user_id: str) -> None:
        deactivate_session(self.sessions_client, user_id)

    def create_event(self, event: CalendarEvent) -> str:
        return create_event(self.events_client, event)

    def find_event_by_id(self, event_id: str, user_id: str) -> Optional[CalendarEvent]:
        return find_event_by_id(self.events_client, event_id, user_id)

    def find_event_by_google_id(self, google_id: str, user_id: str) -> Optional[CalendarEvent]:
        return find_event_by_google_id(self.events_client, google_id, user_id)

    def find_events_by_user(
        self,
        user_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[CalendarEvent]:
        return find_events_by_user(self.events_client, user_id, start, end, limit)

    def update_event(self, event: CalendarEvent) -> None:
        update_event(self.events_client, event)

    def delete_event(self, event_id: str, user_id: str) -> None:
        delete_event(self.events_client, event_id, user_id)
