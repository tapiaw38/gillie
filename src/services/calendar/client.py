import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class GoogleCalendarClient:
    """
    Wrapper for the Google Calendar API.
    Handles OAuth2 flow and calendar event operations.
    Requires: google-api-python-client, google-auth, google-auth-oauthlib
    """

    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> tuple:
        """Return (authorization_url, code_verifier). Caller must store code_verifier for later exchange."""
        flow = self._build_flow()
        auth_url, _ = flow.authorization_url(
            state=state,
            access_type="offline",
            prompt="consent",
        )
        return auth_url, getattr(flow, "code_verifier", None)

    def exchange_code(self, code: str, code_verifier: Optional[str] = None) -> Dict[str, Any]:
        """Exchange authorization code for tokens. Pass code_verifier if PKCE was used."""
        flow = self._build_flow()
        fetch_kwargs = {"code": code}
        if code_verifier:
            fetch_kwargs["code_verifier"] = code_verifier
        flow.fetch_token(**fetch_kwargs)
        creds = flow.credentials
        return {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "expiry": creds.expiry,
            "scopes": list(creds.scopes or self.SCOPES),
        }

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token.
        Returns dict with: access_token, expiry
        """
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES,
        )
        creds.refresh(Request())
        return {"access_token": creds.token, "expiry": creds.expiry}

    # ── Service builder ──────────────────────────────────────────────────────

    def build_service(self, access_token: str, refresh_token: str, expiry: datetime):
        """Build an authenticated Google Calendar service object."""
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            expiry=expiry,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES,
        )
        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    def create_event(self, service, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an event in Google Calendar. Returns the created event."""
        event = service.events().insert(calendarId="primary", body=event_data).execute()
        logger.info(f"Google Calendar event created: {event.get('id')}")
        return event

    def update_event(self, service, google_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing event in Google Calendar."""
        event = (
            service.events()
            .update(calendarId="primary", eventId=google_id, body=event_data)
            .execute()
        )
        logger.info(f"Google Calendar event updated: {google_id}")
        return event

    def delete_event(self, service, google_id: str) -> None:
        """Delete an event from Google Calendar."""
        service.events().delete(calendarId="primary", eventId=google_id).execute()
        logger.info(f"Google Calendar event deleted: {google_id}")

    def get_event(self, service, google_id: str) -> Dict[str, Any]:
        """Fetch a single event by its Google Calendar ID."""
        return service.events().get(calendarId="primary", eventId=google_id).execute()

    def list_events(
        self,
        service,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List upcoming events, optionally filtered by date range."""
        now = datetime.utcnow()
        kwargs: Dict[str, Any] = {
            "calendarId": "primary",
            "timeMin": (time_min or now).isoformat() + "Z",
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": min(limit, 2500),
        }
        if time_max:
            kwargs["timeMax"] = time_max.isoformat() + "Z"
        result = service.events().list(**kwargs).execute()
        return result.get("items", [])

    def _build_flow(self):
        from google_auth_oauthlib.flow import Flow

        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri],
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri,
        )
        return flow

    @staticmethod
    def build_event_body(
        title: str,
        start_time: datetime,
        end_time: datetime,
        time_zone: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[dict]] = None,
        reminders: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """Build a Google Calendar event body dict.

        When time_zone is None the datetime strings already carry offset info
        (tz-aware isoformat), so no timeZone field is added and Google Calendar
        uses the embedded offset directly.
        """
        def _dt_field(dt: datetime, tz: Optional[str]) -> dict:
            if tz:
                return {"dateTime": dt.isoformat(), "timeZone": tz}
            return {"dateTime": dt.isoformat()}

        body: Dict[str, Any] = {
            "summary": title,
            "start": _dt_field(start_time, time_zone),
            "end": _dt_field(end_time, time_zone),
        }
        if description:
            body["description"] = description
        if location:
            body["location"] = location
        if attendees:
            body["attendees"] = [
                {"email": a.get("email"), "displayName": a.get("name", "")}
                for a in attendees
            ]
        if reminders:
            body["reminders"] = {
                "useDefault": False,
                "overrides": [
                    {"method": r.get("method", "popup"), "minutes": r.get("minutes", 30)}
                    for r in reminders
                ],
            }
        return body
