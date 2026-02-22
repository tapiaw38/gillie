from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .api_key import ApiKey
from ..file.file import File
from ..integration.integration import Integration


class Profile(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    assistant_name: Optional[str] = None
    business_name: Optional[str] = None
    functions: Optional[str] = None
    business_context: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[str] = None
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    is_active: Optional[bool] = Field(default=True)
    tts_enabled: Optional[bool] = Field(default=False)
    api_keys: Optional[List[ApiKey]] = Field(default=None)
    files: Optional[List[File]] = Field(default=None)
    integrations: Optional[List[Integration]] = Field(default=None)

    class Config:
        allow_population_by_field_name = True
