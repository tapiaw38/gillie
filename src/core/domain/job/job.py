from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime


class Job(BaseModel):
    id: str
    profile_id: str
    name: str
    description: str = ""
    cron_expr: str  # standard 5-field cron: "*/5 * * * *"

    # Source -- what produces the data
    source_type: str  # "system_command" | "http_get" | "db_query" | "static"
    source_params: Dict[str, Any] = {}

    # Destination -- where to send the result
    destination_type: str  # "whatsapp" | "telegram" | "slack" | "none"
    destination_params: Dict[str, Any] = {}

    # Message formatting
    message_template: str = "{{output}}"  # {{output}} replaced with source result

    enabled: bool = True
    status: str = "idle"  # "idle" | "running" | "failed"
    last_run_at: Optional[datetime] = None
    last_result: Optional[str] = None
    created_at: datetime
    updated_at: datetime
