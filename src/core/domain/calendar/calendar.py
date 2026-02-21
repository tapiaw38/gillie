from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CalendarSession(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    access_token: str
    refresh_token: str
    token_expiry: datetime
    scopes: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    class Config:
        allow_population_by_field_name = True


class CalendarEvent(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    google_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime
    end_time: datetime
    time_zone: str = "UTC"
    attendees: List[dict] = Field(default_factory=list)
    reminders: List[dict] = Field(default_factory=list)
    status: str = "scheduled"
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    class Config:
        allow_population_by_field_name = True
