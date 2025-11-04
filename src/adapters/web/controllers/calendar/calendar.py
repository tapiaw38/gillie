from fastapi import APIRouter, Depends, Request, status
from src.schemas.calendar import (
    CalendarEventInput,
    CalendarEventOutput,
    CalendarEventListOutput,
    CalendarAuthorizationOutput,
    CalendarStatusOutput,
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
    """Set the usecases instance (called during app initialization)"""
    global _usecases_instance
    _usecases_instance = usecases

def get_usecases() -> Usecases:
    """Get the usecases instance for dependency injection"""
    if _usecases_instance is None:
        raise Exception("Usecases not initialized. Call set_usecases first.")
    return _usecases_instance


@router.get("/authorize", response_model=CalendarAuthorizationOutput, status_code=status.HTTP_200_OK)
async def get_authorization_url(
    request: Request,
    usecases: Usecases = Depends(get_usecases)
):
    """
    Get Google Calendar OAuth authorization URL for the current user.

    This endpoint returns the URL where users should be redirected to authorize
    the application to access their Google Calendar.
    """
    user_id = request.state.user.get("user_id")
    profile_id = request.query_params.get("profile_id", user_id)

    auth_url = usecases.calendar.get_authorization_url_usecase.execute(user_id, profile_id)

    return CalendarAuthorizationOutput(
        authorization_url=auth_url,
        user_id=user_id,
        profile_id=profile_id
    )


@router.get("/status", response_model=CalendarStatusOutput, status_code=status.HTTP_200_OK)
async def check_calendar_status(
    request: Request,
    profile_id: Optional[str] = None,
    usecases: Usecases = Depends(get_usecases)
):
    """
    Check if the user has an active Google Calendar session.

    Returns:
        is_active: True if user has authorized and session is active
    """
    user_id = request.state.user.get("user_id")
    profile_id = profile_id or user_id

    is_active = usecases.calendar.check_session_status_usecase.execute(user_id, profile_id)

    return CalendarStatusOutput(
        is_active=is_active,
        user_id=user_id,
        profile_id=profile_id
    )


@router.post("/events", response_model=CalendarEventOutput, status_code=status.HTTP_201_CREATED)
async def create_calendar_event(
    event: CalendarEventInput,
    request: Request,
    profile_id: Optional[str] = None,
    usecases: Usecases = Depends(get_usecases)
):
    """
    Create a new calendar event.

    The event will be created in the user's Google Calendar and stored locally.
    """
    user_id = request.state.user.get("user_id")
    profile_id = profile_id or user_id

    jwt_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        jwt_token = auth_header.split(" ")[1]

    attendees = None
    if event.attendees:
        attendees = [{"email": a.email, "name": a.name} for a in event.attendees]

    reminders = None
    if event.reminders:
        reminders = [{"method": r.method, "minutes": r.minutes} for r in event.reminders]

    created_event = usecases.calendar.create_event_usecase.execute(
        user_id=user_id,
        profile_id=profile_id,
        title=event.title,
        start_time=event.start_time,
        end_time=event.end_time,
        description=event.description,
        location=event.location,
        attendees=attendees,
        reminders=reminders,
        jwt_token=jwt_token
    )

    return CalendarEventOutput(**created_event)


@router.get("/events", response_model=CalendarEventListOutput, status_code=status.HTTP_200_OK)
async def list_calendar_events(
    request: Request,
    profile_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    usecases: Usecases = Depends(get_usecases)
):
    """
    List calendar events for the user.

    Optionally filter by date range.
    """
    user_id = request.state.user.get("user_id")
    profile_id = profile_id or user_id

    jwt_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        jwt_token = auth_header.split(" ")[1]

    events = usecases.calendar.list_events_usecase.execute(
        user_id=user_id,
        profile_id=profile_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        jwt_token=jwt_token
    )

    event_outputs = [CalendarEventOutput(**event) for event in events]

    return CalendarEventListOutput(data=event_outputs)


@router.put("/events/{event_id}", response_model=CalendarEventOutput, status_code=status.HTTP_200_OK)
async def update_calendar_event(
    event_id: str,
    event: CalendarEventInput,
    request: Request,
    profile_id: Optional[str] = None,
    usecases: Usecases = Depends(get_usecases)
):
    """
    Update an existing calendar event.
    """
    user_id = request.state.user.get("user_id")
    profile_id = profile_id or user_id

    jwt_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        jwt_token = auth_header.split(" ")[1]

    updated_event = usecases.calendar.update_event_usecase.execute(
        event_id=event_id,
        user_id=user_id,
        profile_id=profile_id,
        title=event.title,
        start_time=event.start_time,
        end_time=event.end_time,
        description=event.description,
        location=event.location,
        jwt_token=jwt_token
    )

    return CalendarEventOutput(**updated_event)


@router.delete("/events/{event_id}", status_code=status.HTTP_200_OK)
async def delete_calendar_event(
    event_id: str,
    request: Request,
    profile_id: Optional[str] = None,
    usecases: Usecases = Depends(get_usecases)
):
    """
    Delete a calendar event.
    """
    user_id = request.state.user.get("user_id")
    profile_id = profile_id or user_id

    jwt_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        jwt_token = auth_header.split(" ")[1]

    usecases.calendar.delete_event_usecase.execute(
        event_id=event_id,
        user_id=user_id,
        profile_id=profile_id,
        jwt_token=jwt_token
    )

    return {"message": "Event deleted successfully", "event_id": event_id}
