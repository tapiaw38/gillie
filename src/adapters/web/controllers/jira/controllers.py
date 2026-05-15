from fastapi import APIRouter, Depends, Request, status
from src.schemas.jira import (
    JiraCreateIssueInput,
    JiraUpdateIssueInput,
    JiraAddCommentInput,
    JiraSearchIssuesInput,
    JiraTransitionIssueInput,
)
from src.core.use_cases.use_cases import Usecases
from src.adapters.web.dependencies import get_usecases
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/jira",
    tags=["jira"],
)


@router.get("/projects", status_code=status.HTTP_200_OK)
async def get_projects(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Return all accessible Jira projects."""
    user_id = request.state.user.get("user_id")
    projects = await usecases.jira.get_projects_usecase.execute(user_id)
    return {"data": projects}


@router.post("/issues/search", status_code=status.HTTP_200_OK)
async def search_issues(
    body: JiraSearchIssuesInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Search Jira issues using JQL."""
    user_id = request.state.user.get("user_id")
    result = await usecases.jira.search_issues_usecase.execute(
        user_id, body.jql, max_results=body.max_results
    )
    return result


@router.post("/issues", status_code=status.HTTP_201_CREATED)
async def create_issue(
    issue: JiraCreateIssueInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Create a new Jira issue."""
    user_id = request.state.user.get("user_id")
    created = await usecases.jira.create_issue_usecase.execute(
        user_id,
        issue.project_key,
        issue.summary,
        issue.issue_type,
        description=issue.description,
        assignee_account_id=issue.assignee_account_id,
        priority=issue.priority,
        labels=issue.labels,
    )
    return created


@router.put("/issues/{issue_key}", status_code=status.HTTP_200_OK)
async def update_issue(
    issue_key: str,
    issue: JiraUpdateIssueInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Update fields of an existing Jira issue."""
    user_id = request.state.user.get("user_id")
    await usecases.jira.update_issue_usecase.execute(
        user_id,
        issue_key,
        summary=issue.summary,
        description=issue.description,
        assignee_account_id=issue.assignee_account_id,
        priority=issue.priority,
        labels=issue.labels,
    )
    return {"message": "Issue updated successfully", "issue_key": issue_key}


@router.get("/issues/{issue_key}/transitions", status_code=status.HTTP_200_OK)
async def get_transitions(
    issue_key: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Return available workflow transitions for a Jira issue."""
    user_id = request.state.user.get("user_id")
    transitions = await usecases.jira.get_transitions_usecase.execute(user_id, issue_key)
    return {"data": transitions}


@router.post("/issues/{issue_key}/transitions", status_code=status.HTTP_200_OK)
async def transition_issue(
    issue_key: str,
    body: JiraTransitionIssueInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Move a Jira issue to a new status via a workflow transition."""
    user_id = request.state.user.get("user_id")
    await usecases.jira.transition_issue_usecase.execute(
        user_id, issue_key, body.transition_id
    )
    return {"message": "Issue transitioned successfully", "issue_key": issue_key}


@router.post("/issues/{issue_key}/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(
    issue_key: str,
    body: JiraAddCommentInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Add a comment to a Jira issue."""
    user_id = request.state.user.get("user_id")
    result = await usecases.jira.add_comment_usecase.execute(
        user_id, issue_key, body.body_text
    )
    return result
