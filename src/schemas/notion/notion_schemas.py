from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class NotionCredentialsInput(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = None


class NotionAuthorizationOutput(BaseModel):
    authorization_url: str
    user_id: str


class NotionStatusOutput(BaseModel):
    is_active: bool
    user_id: str
    workspace_name: Optional[str] = None
    workspace_icon: Optional[str] = None
    owner_name: Optional[str] = None


class NotionSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    next_cursor: Optional[str] = None
    has_more: bool = False


class NotionPageResponse(BaseModel):
    data: Dict[str, Any]
