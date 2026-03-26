from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AttendeeInput(BaseModel):
    email: str
    name: Optional[str] = None


class ReminderInput(BaseModel):
    method: str  # "email" or "popup"
    minutes: int  # minutes before event


class CalendarEventInput(BaseModel):
    """Schema for creating/updating calendar events"""
    title: str
    start_time: str  # ISO 8601 format
    end_time: str  # ISO 8601 format
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[AttendeeInput]] = None
    reminders: Optional[List[ReminderInput]] = None


class CalendarEventOutput(BaseModel):
    """Schema for calendar event response"""
    id: str
    user_id: str
    profile_id: Optional[str] = None
    google_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: str
    end_time: str
    time_zone: str
    attendees: Optional[List[Dict[str, Any]]] = None
    reminders: Optional[List[Dict[str, Any]]] = None
    status: str
    created_at: str
    updated_at: str


class CalendarEventListOutput(BaseModel):
    """Schema for listing calendar events"""
    data: List[CalendarEventOutput]


class CalendarAuthorizationOutput(BaseModel):
    """Schema for Google Calendar authorization"""
    authorization_url: str
    user_id: str
    profile_id: Optional[str] = None


class CalendarStatusOutput(BaseModel):
    """Schema for calendar session status"""
    is_active: bool
    user_id: str
    profile_id: Optional[str] = None


class CalendarCredentialsInput(BaseModel):
    """Schema for saving Google OAuth2 app credentials"""
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = None
