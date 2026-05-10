from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse
from src.schemas.calendar import (
    CalendarEventInput,
    CalendarEventOutput,
    CalendarEventListOutput,
    CalendarAuthorizationOutput,
    CalendarStatusOutput,
    CalendarCredentialsInput,
)
from src.core.use_cases.use_cases import Usecases
from src.adapters.web.dependencies import get_usecases
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/calendar",
    tags=["calendar"],
)


@router.get("/credentials", status_code=status.HTTP_200_OK)
async def get_calendar_credentials(
    usecases: Usecases = Depends(get_usecases),
):
    """Get saved Google Calendar OAuth credentials (client_id only, secret never returned)."""
    return await usecases.calendar.get_credentials_usecase.execute() or {}


@router.post("/credentials", status_code=status.HTTP_200_OK)
async def set_calendar_credentials(
    creds: CalendarCredentialsInput,
    usecases: Usecases = Depends(get_usecases),
):
    """Save Google OAuth2 app credentials (client_id / client_secret) to MongoDB."""
    redirect_uri = creds.redirect_uri or "http://localhost:8000/api/v1/calendar/oauth/callback"
    await usecases.calendar.set_credentials_usecase.execute(
        creds.client_id,
        creds.client_secret,
        redirect_uri,
    )
    return {"message": "Credentials saved successfully"}


@router.get("/authorize", response_model=CalendarAuthorizationOutput, status_code=status.HTTP_200_OK)
async def get_authorization_url(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Get Google Calendar OAuth authorization URL for the current user."""
    user_id = request.state.user.get("user_id")
    auth_url = await usecases.calendar.get_authorization_url_usecase.execute(user_id)
    return CalendarAuthorizationOutput(
        authorization_url=auth_url,
        user_id=user_id,
        profile_id=user_id,
    )


@router.get("/oauth/callback", response_class=HTMLResponse)
async def oauth_callback(
    request: Request,
    code: str,
    state: Optional[str] = None,
    usecases: Usecases = Depends(get_usecases),
):
    """
    Handle Google OAuth2 callback.
    Google redirects here after the user grants access.
    `state` carries the user_id set during authorization.
    Returns an HTML page that closes the popup window.
    """
    user_id = state or request.state.user.get("user_id")
    await usecases.calendar.handle_oauth_callback_usecase.execute(user_id, code)
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head><title>Autorización exitosa</title></head>
<body>
<p>Autorización exitosa. Cerrando ventana...</p>
<script>
  if (window.opener) {
    try { window.opener.postMessage({ type: 'oauth_success', integration: 'google_calendar' }, '*'); } catch(e) {}
  }
  window.close();
</script>
</body>
</html>
""")


@router.get("/status", response_model=CalendarStatusOutput, status_code=status.HTTP_200_OK)
async def check_calendar_status(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Check if the user has an active Google Calendar session."""
    user_id = request.state.user.get("user_id")
    is_active = await usecases.calendar.check_session_status_usecase.execute(user_id)
    return CalendarStatusOutput(
        is_active=is_active,
        user_id=user_id,
        profile_id=user_id,
    )


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_calendar(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Disconnect (revoke) the Google Calendar OAuth session."""
    user_id = request.state.user.get("user_id")
    await usecases.calendar.disconnect_usecase.execute(user_id)


@router.post("/events", response_model=CalendarEventOutput, status_code=status.HTTP_201_CREATED)
async def create_calendar_event(
    event: CalendarEventInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Create a new calendar event."""
    user_id = request.state.user.get("user_id")

    attendees = None
    if event.attendees:
        attendees = [{"email": a.email, "name": a.name} for a in event.attendees]

    reminders = None
    if event.reminders:
        reminders = [{"method": r.method, "minutes": r.minutes} for r in event.reminders]

    created_event = await usecases.calendar.create_event_usecase.execute(
        user_id,
        event.title,
        event.start_time,
        event.end_time,
        event.description,
        event.location,
        attendees,
        reminders,
    )

    return CalendarEventOutput(**created_event)


@router.get("/events", response_model=CalendarEventListOutput, status_code=status.HTTP_200_OK)
async def list_calendar_events(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    usecases: Usecases = Depends(get_usecases),
):
    """List calendar events for the user."""
    user_id = request.state.user.get("user_id")

    events = await usecases.calendar.list_events_usecase.execute(
        user_id,
        start_date,
        end_date,
        limit,
    )

    event_outputs = [CalendarEventOutput(**e) for e in events]
    return CalendarEventListOutput(data=event_outputs)


@router.put("/events/{event_id}", response_model=CalendarEventOutput, status_code=status.HTTP_200_OK)
async def update_calendar_event(
    event_id: str,
    event: CalendarEventInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Update an existing calendar event. event_id is the Google Calendar event ID."""
    user_id = request.state.user.get("user_id")

    updated_event = await usecases.calendar.update_event_usecase.execute(
        user_id,
        event_id,
        event.title,
        event.start_time,
        event.end_time,
        event.description,
        event.location,
    )

    return CalendarEventOutput(**updated_event)


@router.delete("/events/{event_id}", status_code=status.HTTP_200_OK)
async def delete_calendar_event(
    event_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Delete a calendar event by its Google Calendar event ID."""
    user_id = request.state.user.get("user_id")

    await usecases.calendar.delete_event_usecase.execute(user_id, event_id)

    return {"message": "Event deleted successfully", "event_id": event_id}
