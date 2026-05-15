import asyncio
import logging
from typing import List, Optional

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.jira import (
    JiraIntegrationNotFoundError,
    JiraIntegrationConfigError,
    JiraIssueUpdateError,
)

logger = logging.getLogger(__name__)


def _find_jira_integration(profile):
    if not profile or not profile.integrations:
        return None
    for integration in profile.integrations:
        if integration.name == "jira" and integration.activated:
            return integration
    return None


class UpdateIssueUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(
        self,
        user_id: str,
        issue_key: str,
        *,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        assignee_account_id: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> None:
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
            await asyncio.to_thread(
                client.update_issue,
                issue_key,
                summary=summary,
                description=description,
                assignee_account_id=assignee_account_id,
                priority=priority,
                labels=labels,
            )
        except Exception as e:
            logger.error(f"Error updating Jira issue {issue_key}: {e}", exc_info=True)
            raise NewApplicationError(JiraIssueUpdateError, e)
