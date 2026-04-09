import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

from src.core.domain.calendar import CalendarSession
from src.services.calendar.client import GoogleCalendarClient
from src.adapters.datasources.repositories.calendar.repository import Repository as CalendarRepository

logger = logging.getLogger(__name__)


class GoogleCalendarIntegration:
    """
    Adapter that wires GoogleCalendarClient (Google API) with CalendarRepository (MongoDB).
    OAuth sessions and app credentials are persisted in MongoDB.
    Calendar events are read/written directly from/to Google Calendar — no local copy.
    """

    def __init__(self, repository: CalendarRepository, fallback_client: Optional[GoogleCalendarClient] = None):
        self.repository = repository
        self._fallback_client = fallback_client
        self._pending_verifiers: Dict[str, str] = {}  # user_id -> code_verifier (PKCE)

    def _get_client(self) -> GoogleCalendarClient:
        """Return a GoogleCalendarClient built from DB credentials, falling back to env-var client."""
        creds = self.repository.find_credentials()
        if creds:
            return GoogleCalendarClient(
                client_id=creds.client_id,
                client_secret=creds.client_secret,
                redirect_uri=creds.redirect_uri,
            )
        if self._fallback_client:
            return self._fallback_client
        raise RuntimeError(
            "Google Calendar credentials not configured. "
            "Use POST /api/v1/calendar/credentials to save client_id and client_secret."
        )

    def get_authorization_url(self, user_id: str) -> str:
        auth_url, code_verifier = self._get_client().get_authorization_url(state=user_id)
        if code_verifier:
            self._pending_verifiers[user_id] = code_verifier
        return auth_url

    def handle_oauth_callback(self, user_id: str, code: str) -> CalendarSession:
        code_verifier = self._pending_verifiers.pop(user_id, None)
        client = self._get_client()
        tokens = client.exchange_code(code, code_verifier=code_verifier)
        session = CalendarSession(
            user_id=user_id,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_expiry=tokens["expiry"],
            scopes=tokens["scopes"],
            is_active=True,
        )

        # Read the user's primary calendar timezone from Google Calendar settings
        try:
            service = client.build_service(
                access_token=session.access_token,
                refresh_token=session.refresh_token,
                expiry=session.token_expiry,
            )
            tz = service.settings().get(setting="timezone").execute().get("value", "UTC")
            session.time_zone = tz
            logger.info(f"Calendar timezone for user_id={user_id}: {tz}")
        except Exception as e:
            logger.warning(f"Could not read calendar timezone for user_id={user_id}: {e}")

        self.repository.upsert_session(session)
        logger.info(f"OAuth session stored for user_id={user_id}")
        return session

    def check_session_status(self, user_id: str) -> bool:
        session = self.repository.find_active_session(user_id)
        if not session:
            return False
        now = datetime.now(timezone.utc)
        expiry = session.token_expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry > now

    def _get_service(self, user_id: str):
        """Return an authenticated Google Calendar service, refreshing token if needed."""
        session = self.repository.find_active_session(user_id)
        if not session:
            raise RuntimeError(f"No active Google Calendar session for user_id={user_id}")

        now = datetime.now(timezone.utc)
        expiry = session.token_expiry
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        client = self._get_client()

        if expiry <= now:
            refreshed = client.refresh_access_token(session.refresh_token)
            session.access_token = refreshed["access_token"]
            session.token_expiry = refreshed["expiry"]
            self.repository.upsert_session(session)

        return client.build_service(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expiry=session.token_expiry,
        )

    def list_events(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        service = self._get_service(user_id)
        client = self._get_client()
        time_min = datetime.fromisoformat(start_date) if start_date else None
        time_max = datetime.fromisoformat(end_date) if end_date else None
        events = client.list_events(service, time_min=time_min, time_max=time_max, limit=limit)
        return [self._google_event_to_dict(e, user_id) for e in events]

    def _resolve_datetime_and_tz(
        self, dt_str: str, fallback_tz: str
    ):
        """Parse a datetime string. If naive, return (dt, fallback_tz). If tz-aware, return (dt, None)
        so that the ISO string (which already includes the offset) is used directly by Google."""
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is not None:
            return dt, None  # isoformat() will include the offset — no timeZone field needed
        return dt, fallback_tz

    def _session_timezone(self, user_id: str) -> str:
        """Return the stored IANA timezone for the user's session.

        If the stored value is 'UTC' (the default/unset value), it tries to
        refresh it once from the Google Calendar Settings API and persists the
        real timezone so future calls are fast.
        """
        try:
            session = self.repository.find_active_session(user_id)
            if session and session.time_zone and session.time_zone != "UTC":
                return session.time_zone

            # Stored as default "UTC" — try to fetch the real timezone from Google
            if session:
                try:
                    service = self._get_service(user_id)
                    tz = service.settings().get(setting="timezone").execute().get("value", "UTC")
                    if tz and tz != "UTC":
                        session.time_zone = tz
                        self.repository.upsert_session(session)
                        logger.info(f"Refreshed timezone for user_id={user_id}: {tz}")
                        return tz
                except Exception as e:
                    logger.warning(f"Could not refresh timezone for user_id={user_id}: {e}")
        except Exception:
            pass
        return "UTC"

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
        time_zone: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        service = self._get_service(user_id)
        client = self._get_client()
        effective_tz = time_zone or self._session_timezone(user_id)
        start_dt, start_tz = self._resolve_datetime_and_tz(start_time, effective_tz)
        end_dt, end_tz = self._resolve_datetime_and_tz(end_time, effective_tz)
        body = GoogleCalendarClient.build_event_body(
            title=title,
            start_time=start_dt,
            end_time=end_dt,
            time_zone=start_tz,
            description=description,
            location=location,
            attendees=attendees,
            reminders=reminders,
        )
        google_event = client.create_event(service, body)
        return self._google_event_to_dict(google_event, user_id)

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
        service = self._get_service(user_id)
        client = self._get_client()

        current = client.get_event(service, event_id)
        current_start = current.get("start", {})
        current_end = current.get("end", {})
        time_zone = current_start.get("timeZone", "UTC")

        effective_tz = time_zone or self._session_timezone(user_id)
        raw_start = start_time or (current_start.get("dateTime") or current_start.get("date", "")).replace("Z", "+00:00")
        raw_end = end_time or (current_end.get("dateTime") or current_end.get("date", "")).replace("Z", "+00:00")
        start_dt, start_tz = self._resolve_datetime_and_tz(raw_start, effective_tz)
        end_dt, _ = self._resolve_datetime_and_tz(raw_end, effective_tz)
        body = GoogleCalendarClient.build_event_body(
            title=title or current.get("summary", ""),
            start_time=start_dt,
            end_time=end_dt,
            time_zone=start_tz,
            description=description if description is not None else current.get("description"),
            location=location if location is not None else current.get("location"),
        )
        updated = client.update_event(service, event_id, body)
        return self._google_event_to_dict(updated, user_id)

    def delete_event(self, user_id: str, event_id: str, **kwargs) -> None:
        service = self._get_service(user_id)
        self._get_client().delete_event(service, event_id)

    @staticmethod
    def _google_event_to_dict(google_event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        start = google_event.get("start", {})
        end = google_event.get("end", {})
        attendees_raw = google_event.get("attendees", [])
        reminders_raw = google_event.get("reminders", {}).get("overrides", [])
        google_id = google_event.get("id", "")
        return {
            "id": google_id,
            "user_id": user_id,
            "google_id": google_id,
            "title": google_event.get("summary", ""),
            "description": google_event.get("description"),
            "location": google_event.get("location"),
            "start_time": start.get("dateTime") or start.get("date", ""),
            "end_time": end.get("dateTime") or end.get("date", ""),
            "time_zone": start.get("timeZone", "UTC"),
            "attendees": [
                {"email": a.get("email", ""), "name": a.get("displayName", "")}
                for a in attendees_raw
            ],
            "reminders": reminders_raw,
            "status": google_event.get("status", "confirmed"),
            "created_at": google_event.get("created", ""),
            "updated_at": google_event.get("updated", ""),
        }
