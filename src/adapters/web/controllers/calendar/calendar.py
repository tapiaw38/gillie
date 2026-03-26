from fastapi import APIRouter, Depends, Request, status
from src.schemas.calendar import (
    CalendarEventInput,
    CalendarEventOutput,
    CalendarEventListOutput,
    CalendarAuthorizationOutput,
    CalendarStatusOutput,
    CalendarCredentialsInput,
)
from src.core.use_cases.use_cases import Usecases
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/calendar",
    tags=["calendar"],
)

_usecases_instance = None


def set_usecases(usecases: Usecases):
    global _usecases_instance
    _usecases_instance = usecases


def get_usecases() -> Usecases:
    if _usecases_instance is None:
        raise Exception("Usecases not initialized. Call set_usecases first.")
    return _usecases_instance


@router.post("/credentials", status_code=status.HTTP_200_OK)
async def set_calendar_credentials(
    creds: CalendarCredentialsInput,
    usecases: Usecases = Depends(get_usecases),
):
    """Save Google OAuth2 app credentials (client_id / client_secret) to MongoDB."""
    redirect_uri = creds.redirect_uri or "http://localhost:8000/api/v1/calendar/oauth/callback"
    usecases.calendar.set_credentials_usecase.execute(
        client_id=creds.client_id,
        client_secret=creds.client_secret,
        redirect_uri=redirect_uri,
    )
    return {"message": "Credentials saved successfully"}


@router.get("/authorize", response_model=CalendarAuthorizationOutput, status_code=status.HTTP_200_OK)
async def get_authorization_url(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Get Google Calendar OAuth authorization URL for the current user."""
    user_id = request.state.user.get("user_id")
    auth_url = usecases.calendar.get_authorization_url_usecase.execute(user_id)
    return CalendarAuthorizationOutput(
        authorization_url=auth_url,
        user_id=user_id,
        profile_id=user_id,
    )


@router.get("/oauth/callback", status_code=status.HTTP_200_OK)
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
    """
    user_id = state or request.state.user.get("user_id")
    usecases.calendar.handle_oauth_callback_usecase.execute(user_id=user_id, code=code)
    return {"message": "Google Calendar connected successfully", "user_id": user_id}


@router.get("/status", response_model=CalendarStatusOutput, status_code=status.HTTP_200_OK)
async def check_calendar_status(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Check if the user has an active Google Calendar session."""
    user_id = request.state.user.get("user_id")
    is_active = usecases.calendar.check_session_status_usecase.execute(user_id)
    return CalendarStatusOutput(
        is_active=is_active,
        user_id=user_id,
        profile_id=user_id,
    )


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

    created_event = usecases.calendar.create_event_usecase.execute(
        user_id=user_id,
        title=event.title,
        start_time=event.start_time,
        end_time=event.end_time,
        description=event.description,
        location=event.location,
        attendees=attendees,
        reminders=reminders,
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

    events = usecases.calendar.list_events_usecase.execute(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
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

    updated_event = usecases.calendar.update_event_usecase.execute(
        user_id=user_id,
        event_id=event_id,
        title=event.title,
        start_time=event.start_time,
        end_time=event.end_time,
        description=event.description,
        location=event.location,
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

    usecases.calendar.delete_event_usecase.execute(
        event_id=event_id,
        user_id=user_id,
    )

    return {"message": "Event deleted successfully", "event_id": event_id}
