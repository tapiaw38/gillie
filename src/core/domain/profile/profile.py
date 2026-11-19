from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from .api_key import ApiKey
from .contact import Contact
from ..file.file import File
from ..integration.integration import Integration


class Profile(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    assistant_name: Optional[str] = None
    functions: Optional[str] = None
    tool_prompts: Optional[str] = None
    disabled_tools: Optional[List[str]] = None
    user_id: Optional[str] = None
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    is_active: Optional[bool] = Field(default=True)
    tts_enabled: Optional[bool] = Field(default=False)
    tts_voice: Optional[str] = Field(default=None)
    tts_engine: Optional[str] = Field(default=None)
    tts_pitch: Optional[float] = Field(default=0.0)
    avatar_width: Optional[int] = Field(default=None)
    avatar_height: Optional[int] = Field(default=None)
    avatar_zoom: Optional[float] = Field(default=None)
    response_language: Optional[str] = Field(default="en")
    active_provider: Optional[str] = Field(default=None)
    provider_keys: Optional[Dict[str, str]] = Field(default=None)
    custom_providers: Optional[Dict[str, Any]] = Field(default=None)
    api_keys: Optional[List[ApiKey]] = Field(default=None)
    contacts: Optional[List[Contact]] = Field(default=None)
    files: Optional[List[File]] = Field(default=None)
    integrations: Optional[List[Integration]] = Field(default=None)
    avatar_assets: Optional[List[Dict[str, Any]]] = Field(default=None)

    class Config:
        populate_by_name = True
