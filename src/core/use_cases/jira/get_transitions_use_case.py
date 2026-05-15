import asyncio
import logging
from typing import Dict, List

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.jira import (
    JiraIntegrationConfigError,
    JiraIntegrationNotFoundError,
    JiraTransitionQueryError,
)

logger = logging.getLogger(__name__)


def _find_jira_integration(profile):
    if not profile or not profile.integrations:
        return None
    for integration in profile.integrations:
        if integration.name == "jira" and integration.activated:
            return integration
    return None


class GetTransitionsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, issue_key: str) -> List[Dict]:
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
            return await asyncio.to_thread(client.get_transitions, issue_key)
        except Exception as e:
            logger.error(f"Error fetching Jira transitions for issue {issue_key}: {e}", exc_info=True)
            raise NewApplicationError(JiraTransitionQueryError, e)
