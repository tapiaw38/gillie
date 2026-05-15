from typing import Any, Dict, Optional
from pydantic import BaseModel


class TeamsActivityInput(BaseModel):
    """Raw Bot Framework Activity payload — passed through to the use case as-is."""
    model_config = {"extra": "allow"}

    type: Optional[str] = None
    id: Optional[str] = None
    serviceUrl: Optional[str] = None
    channelId: Optional[str] = None
    text: Optional[str] = None
