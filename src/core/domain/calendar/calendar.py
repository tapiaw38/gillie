from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CalendarCredentials(BaseModel):
    """Google OAuth2 app credentials stored in MongoDB."""
    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8000/api/v1/calendar/oauth/callback"


class CalendarSession(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    access_token: str
    refresh_token: str
    token_expiry: datetime
    scopes: List[str] = Field(default_factory=list)
    is_active: bool = True
    time_zone: str = "UTC"
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    class Config:
        allow_population_by_field_name = True


