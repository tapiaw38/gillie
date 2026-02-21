import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from src.core.domain.calendar import CalendarSession, CalendarEvent
from src.services.calendar.client import GoogleCalendarClient
from src.adapters.datasources.repositories.calendar.repository import Repository as CalendarRepository

logger = logging.getLogger(__name__)


class GoogleCalendarIntegration:
    """
    Adapter that wires GoogleCalendarClient (Google API) with CalendarRepository (MongoDB).
    Replaces the former HTTP client to calendar-api-be microservice.
    """

    def __init__(self, client: GoogleCalendarClient, repository: CalendarRepository):
        self.client = client
        self.repository = repository

    # ── OAuth ──────────────────────────────────────────────────────────────────

    def get_authorization_url(self, user_id: str) -> str:
        """Return the Google OAuth2 authorization URL."""
        return self.client.get_authorization_url(state=user_id)

    def handle_oauth_callback(self, user_id: str, code: str) -> CalendarSession:
        """
        Exchange the authorization code for tokens, persist the session and return it.
        """
        tokens = self.client.exchange_code(code)

        session = CalendarSession(
            user_id=user_id,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_expiry=tokens["expiry"],
            scopes=tokens["scopes"],
            is_active=True,
        )
        self.repository.upsert_session(session)
        logger.info(f"OAuth session stored for user_id={user_id}")
        return session

    def check_session_status(self, user_id: str) -> bool:
        """Return True if the user has an active, non-expired session."""
        session = self.repository.find_active_session(user_id)
        if not session:
            return False
        now = datetime.now(timezone.utc)
        expiry = session.token_expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry > now

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _get_service(self, user_id: str):
        """
        Return an authenticated Google Calendar service, refreshing token if needed.
        Raises RuntimeError when no active session exists.
        """
        session = self.repository.find_active_session(user_id)
        if not session:
            raise RuntimeError(f"No active Google Calendar session for user_id={user_id}")

        now = datetime.now(timezone.utc)
        expiry = session.token_expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if expiry <= now:
            refreshed = self.client.refresh_access_token(session.refresh_token)
            session.access_token = refreshed["access_token"]
            session.token_expiry = refreshed["expiry"]
            self.repository.upsert_session(session)

        return self.client.build_service(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expiry=session.token_expiry,
        )

    # ── Events ─────────────────────────────────────────────────────────────────

    def create_event(
        self,
        user_id: str,
        title: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[Dict]] = None,
        reminders: Optional[List[Dict]] = None,
        time_zone: str = "UTC",
        **kwargs,
    ) -> Dict[str, Any]:
        service = self._get_service(user_id)

        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)

        body = GoogleCalendarClient.build_event_body(
            title=title,
            start_time=start_dt,
            end_time=end_dt,
            time_zone=time_zone,
            description=description,
            location=location,
            attendees=attendees,
            reminders=reminders,
        )

        google_event = self.client.create_event(service, body)

        event = CalendarEvent(
            user_id=user_id,
            google_id=google_event.get("id"),
            title=title,
            description=description,
            location=location,
            start_time=start_dt,
            end_time=end_dt,
            time_zone=time_zone,
            attendees=attendees or [],
            reminders=reminders or [],
            status="scheduled",
        )
        event_id = self.repository.create_event(event)

        return self._event_to_dict(event, event_id)

    def list_events(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        events = self.repository.find_events_by_user(
            user_id=user_id,
            start=start,
            end=end,
            limit=limit,
        )
        return [self._event_to_dict(e) for e in events]

    def update_event(
        self,
        user_id: str,
        event_id: str,
        title: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        event = self.repository.find_event_by_id(event_id, user_id)
        if not event:
            raise ValueError(f"Event not found: event_id={event_id}")

        if title is not None:
            event.title = title
        if description is not None:
            event.description = description
        if location is not None:
            event.location = location
        if start_time is not None:
            event.start_time = datetime.fromisoformat(start_time)
        if end_time is not None:
            event.end_time = datetime.fromisoformat(end_time)

        if event.google_id:
            service = self._get_service(user_id)
            body = GoogleCalendarClient.build_event_body(
                title=event.title,
                start_time=event.start_time,
                end_time=event.end_time,
                time_zone=event.time_zone,
                description=event.description,
                location=event.location,
                attendees=event.attendees,
                reminders=event.reminders,
            )
            self.client.update_event(service, event.google_id, body)

        self.repository.update_event(event)
        return self._event_to_dict(event)

    def delete_event(self, user_id: str, event_id: str, **kwargs) -> None:
        event = self.repository.find_event_by_id(event_id, user_id)
        if not event:
            raise ValueError(f"Event not found: event_id={event_id}")

        if event.google_id:
            service = self._get_service(user_id)
            self.client.delete_event(service, event.google_id)

        self.repository.delete_event(event_id, user_id)

    def sync_events(self, user_id: str) -> Dict[str, Any]:
        """
        Pull events from Google Calendar for the next 30 days and upsert them locally.
        Returns a summary dict.
        """
        service = self._get_service(user_id)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        from datetime import timedelta
        time_max = now + timedelta(days=30)

        google_events = self.client.list_events(service, time_min=now, time_max=time_max)

        synced = 0
        for ge in google_events:
            google_id = ge.get("id")
            existing = self.repository.find_event_by_google_id(google_id, user_id)

            start_raw = ge.get("start", {})
            end_raw = ge.get("end", {})
            start_str = start_raw.get("dateTime") or start_raw.get("date", "")
            end_str = end_raw.get("dateTime") or end_raw.get("date", "")

            try:
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Skipping event with unparseable time: {google_id}")
                continue

            if existing:
                existing.title = ge.get("summary", existing.title)
                existing.start_time = start_dt
                existing.end_time = end_dt
                self.repository.update_event(existing)
            else:
                event = CalendarEvent(
                    user_id=user_id,
                    google_id=google_id,
                    title=ge.get("summary", "(no title)"),
                    description=ge.get("description"),
                    location=ge.get("location"),
                    start_time=start_dt,
                    end_time=end_dt,
                    time_zone=start_raw.get("timeZone", "UTC"),
                    status="scheduled",
                )
                self.repository.create_event(event)
            synced += 1

        return {"synced": synced, "user_id": user_id}

    # ── Serialization ──────────────────────────────────────────────────────────

    @staticmethod
    def _event_to_dict(event: CalendarEvent, override_id: Optional[str] = None) -> Dict[str, Any]:
        event_id = override_id or event.id or ""
        return {
            "id": event_id,
            "user_id": event.user_id,
            "google_id": event.google_id,
            "title": event.title,
            "description": event.description,
            "location": event.location,
            "start_time": event.start_time.isoformat() if event.start_time else "",
            "end_time": event.end_time.isoformat() if event.end_time else "",
            "time_zone": event.time_zone,
            "attendees": event.attendees,
            "reminders": event.reminders,
            "status": event.status,
            "created_at": event.created_at.isoformat() if event.created_at else "",
            "updated_at": event.updated_at.isoformat() if event.updated_at else "",
        }
