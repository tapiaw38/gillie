from fastapi import APIRouter, Depends, Request, status
from src.schemas.clickup import (
    ClickUpCreateTaskInput,
    ClickUpUpdateTaskInput,
    ClickUpAddCommentInput,
)
from src.core.use_cases.use_cases import Usecases
from src.adapters.web.dependencies import get_usecases
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/clickup",
    tags=["clickup"],
)


@router.get("/workspaces", status_code=status.HTTP_200_OK)
async def get_workspaces(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Return all ClickUp workspaces (teams) the configured token has access to."""
    user_id = request.state.user.get("user_id")
    teams = await usecases.clickup.get_workspaces_usecase.execute(user_id)
    return {"data": teams}


@router.get("/lists/{list_id}/tasks", status_code=status.HTTP_200_OK)
async def get_tasks(
    list_id: str,
    request: Request,
    include_closed: bool = False,
    statuses: list[str] | None = None,
    usecases: Usecases = Depends(get_usecases),
):
    """Return tasks in a ClickUp list."""
    user_id = request.state.user.get("user_id")
    tasks = await usecases.clickup.get_tasks_usecase.execute(
        user_id,
        list_id,
        include_closed=include_closed,
        statuses=statuses,
    )
    return {"data": tasks}


@router.post("/lists/{list_id}/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(
    list_id: str,
    task: ClickUpCreateTaskInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Create a new task in a ClickUp list."""
    user_id = request.state.user.get("user_id")
    created = await usecases.clickup.create_task_usecase.execute(
        user_id,
        list_id,
        task.name,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        assignees=task.assignees,
        tags=task.tags,
    )
    return created


@router.put("/tasks/{task_id}", status_code=status.HTTP_200_OK)
async def update_task(
    task_id: str,
    task: ClickUpUpdateTaskInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Update an existing ClickUp task."""
    user_id = request.state.user.get("user_id")
    updated = await usecases.clickup.update_task_usecase.execute(
        user_id,
        task_id,
        name=task.name,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
    )
    return updated


@router.post("/tasks/{task_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(
    task_id: str,
    body: ClickUpAddCommentInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Add a comment to a ClickUp task."""
    user_id = request.state.user.get("user_id")
    result = await usecases.clickup.add_comment_usecase.execute(
        user_id, task_id, body.comment_text
    )
    return result
