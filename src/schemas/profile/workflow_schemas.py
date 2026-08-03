from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class WorkflowStepInput(BaseModel):
    """A single workflow step, as the visual editor holds it."""

    name: str = Field(default="test_step")
    url: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    headers: Optional[Dict[str, str]] = None
    body_template: Optional[str] = None
    response_mapping: Optional[Dict[str, str]] = None
    condition: Optional[str] = None
    timeout: Optional[float] = None


class WorkflowStepTestInput(BaseModel):
    """Run one step with a sample context, without saving the workflow."""

    step: WorkflowStepInput
    context: Dict[str, Any] = Field(default_factory=dict)
