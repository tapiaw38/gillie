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

    def get_authorization_url(self, state: str) -> str:
        """Return the Google OAuth2 authorization URL."""
        from google_auth_oauthlib.flow import Flow

        flow = self._build_flow()
        auth_url, _ = flow.authorization_url(
            state=state,
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )
        return auth_url

    def exchange_code(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens.
        Returns dict with: access_token, refresh_token, expiry, scopes
        """
        from google_auth_oauthlib.flow import Flow

        flow = self._build_flow()
        flow.fetch_token(code=code)
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

    def list_events(
        self,
        service,
        time_min: datetime,
        time_max: datetime,
    ) -> List[Dict[str, Any]]:
        """List events in a date range for sync."""
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min.isoformat() + "Z",
                timeMax=time_max.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
                maxResults=500,
            )
            .execute()
        )
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
        time_zone: str = "UTC",
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[dict]] = None,
        reminders: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """Build a Google Calendar event body dict."""
        body: Dict[str, Any] = {
            "summary": title,
            "start": {"dateTime": start_time.isoformat(), "timeZone": time_zone},
            "end": {"dateTime": end_time.isoformat(), "timeZone": time_zone},
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
