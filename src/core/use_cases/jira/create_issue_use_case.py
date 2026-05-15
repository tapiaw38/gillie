import asyncio
import logging
from typing import Dict, List, Optional

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.jira import (
    JiraIntegrationNotFoundError,
    JiraIntegrationConfigError,
    JiraIssueCreateError,
    JiraIssueSummaryRequiredError,
    JiraProjectKeyRequiredError,
)

logger = logging.getLogger(__name__)


def _find_jira_integration(profile):
    if not profile or not profile.integrations:
        return None
    for integration in profile.integrations:
        if integration.name == "jira" and integration.activated:
            return integration
    return None


class CreateIssueUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(
        self,
        user_id: str,
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        *,
        description: Optional[str] = None,
        assignee_account_id: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Dict:
        if not summary or not summary.strip():
            raise NewApplicationError(JiraIssueSummaryRequiredError)
        if not project_key or not project_key.strip():
            raise NewApplicationError(JiraProjectKeyRequiredError)

        context = self.context_factory()
        profile = await context.repositories.profile.find_by_user_id(user_id)

        integration = _find_jira_integration(profile)
        if not integration:
            raise NewApplicationError(JiraIntegrationNotFoundError)

        cfg = integration.config
        if not cfg.get("domain") or not cfg.get("email") or not cfg.get("api_token"):
            raise NewApplicationError(JiraIntegrationConfigError)

        try:
            client = context.integrations.make_jira_client(
                domain=cfg["domain"],
                email=cfg["email"],
                api_token=cfg["api_token"],
            )
            issue = await asyncio.to_thread(
                client.create_issue,
                project_key,
                summary,
                issue_type,
                description=description,
                assignee_account_id=assignee_account_id,
                priority=priority,
                labels=labels,
            )
            return issue
        except Exception as e:
            logger.error(f"Error creating Jira issue: {e}", exc_info=True)
            raise NewApplicationError(JiraIssueCreateError, e)
