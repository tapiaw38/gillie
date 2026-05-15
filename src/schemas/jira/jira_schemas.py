from typing import List, Optional
from pydantic import BaseModel, Field


class JiraCreateIssueInput(BaseModel):
    project_key: str = Field(..., description="Jira project key, e.g. 'PROJ'")
    summary: str = Field(..., description="Issue summary/title")
    issue_type: str = Field(default="Task", description="Issue type: Task, Bug, Story, Epic, etc.")
    description: Optional[str] = Field(default=None, description="Issue description (plain text)")
    assignee_account_id: Optional[str] = Field(default=None, description="Assignee Jira account ID")
    priority: Optional[str] = Field(default=None, description="Priority: Highest, High, Medium, Low, Lowest")
    labels: Optional[List[str]] = Field(default=None, description="List of label strings")


class JiraUpdateIssueInput(BaseModel):
    summary: Optional[str] = Field(default=None, description="New summary")
    description: Optional[str] = Field(default=None, description="New description (plain text)")
    assignee_account_id: Optional[str] = Field(default=None, description="New assignee account ID")
    priority: Optional[str] = Field(default=None, description="New priority")
    labels: Optional[List[str]] = Field(default=None, description="New labels list")


class JiraAddCommentInput(BaseModel):
    body_text: str = Field(..., description="Plain-text comment body")


class JiraSearchIssuesInput(BaseModel):
    jql: str = Field(..., description="JQL query string, e.g. 'project = PROJ AND status = \"In Progress\"'")
    max_results: int = Field(default=50, description="Maximum number of issues to return")


class JiraTransitionIssueInput(BaseModel):
    transition_id: str = Field(..., description="Transition ID (get from GET /transitions endpoint)")
