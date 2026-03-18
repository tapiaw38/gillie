from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class JobInput(BaseModel):
    name: str = Field(..., description="Job name", min_length=1)
    description: str = Field("", description="Job description")
    cron_expr: str = Field(..., description="5-field cron expression, e.g. '*/5 * * * *'")
    source_type: str = Field(..., description="Source type: system_command, http_get, db_query, static")
    source_params: Dict[str, Any] = Field(default_factory=dict, description="Source parameters")
    destination_type: str = Field(..., description="Destination type: whatsapp, telegram, slack, none")
    destination_params: Dict[str, Any] = Field(default_factory=dict, description="Destination parameters")
    message_template: str = Field("{{output}}", description="Message template with {{output}} placeholder")
    enabled: bool = Field(True, description="Whether the job is enabled")


class JobUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cron_expr: Optional[str] = None
    source_type: Optional[str] = None
    source_params: Optional[Dict[str, Any]] = None
    destination_type: Optional[str] = None
    destination_params: Optional[Dict[str, Any]] = None
    message_template: Optional[str] = None
    enabled: Optional[bool] = None


class JobData(BaseModel):
    id: str
    profile_id: str
    name: str
    description: str = ""
    cron_expr: str
    source_type: str
    source_params: Dict[str, Any] = {}
    destination_type: str
    destination_params: Dict[str, Any] = {}
    message_template: str = "{{output}}"
    enabled: bool = True
    status: str = "idle"
    last_run_at: Optional[str] = None
    last_result: Optional[str] = None
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, job) -> "JobData":
        return cls(
            id=job.id,
            profile_id=job.profile_id,
            name=job.name,
            description=job.description,
            cron_expr=job.cron_expr,
            source_type=job.source_type,
            source_params=job.source_params,
            destination_type=job.destination_type,
            destination_params=job.destination_params,
            message_template=job.message_template,
            enabled=job.enabled,
            status=job.status,
            last_run_at=job.last_run_at.isoformat() if job.last_run_at else None,
            last_result=job.last_result,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
        )


class JobOutput(BaseModel):
    data: JobData


class JobListOutput(BaseModel):
    data: List[JobData]


class JobRunOutput(BaseModel):
    status: str
    result: Optional[str] = None
