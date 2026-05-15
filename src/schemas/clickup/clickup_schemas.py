from typing import List, Optional
from pydantic import BaseModel, Field


class ClickUpCreateTaskInput(BaseModel):
    name: str = Field(..., description="Task name")
    description: Optional[str] = Field(default=None, description="Task description")
    status: Optional[str] = Field(default=None, description="Task status (e.g. 'to do', 'in progress')")
    priority: Optional[int] = Field(default=None, description="Priority: 1=urgent, 2=high, 3=normal, 4=low")
    due_date: Optional[int] = Field(default=None, description="Due date as Unix timestamp in milliseconds")
    assignees: Optional[List[int]] = Field(default=None, description="List of assignee user IDs")
    tags: Optional[List[str]] = Field(default=None, description="List of tag names")


class ClickUpUpdateTaskInput(BaseModel):
    name: Optional[str] = Field(default=None, description="New task name")
    description: Optional[str] = Field(default=None, description="New task description")
    status: Optional[str] = Field(default=None, description="New status")
    priority: Optional[int] = Field(default=None, description="New priority: 1=urgent, 2=high, 3=normal, 4=low")
    due_date: Optional[int] = Field(default=None, description="New due date as Unix timestamp in milliseconds")


class ClickUpAddCommentInput(BaseModel):
    comment_text: str = Field(..., description="Plain-text comment to add to the task")


class ClickUpGetTasksInput(BaseModel):
    include_closed: bool = Field(default=False, description="Include closed/completed tasks")
    statuses: Optional[List[str]] = Field(default=None, description="Filter by status names")
