import asyncio
import logging
from typing import Dict, List

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.clickup import (
    ClickUpIntegrationNotFoundError,
    ClickUpIntegrationConfigError,
    ClickUpWorkspaceQueryError,
)

logger = logging.getLogger(__name__)


def _find_clickup_integration(profile):
    if not profile or not profile.integrations:
        return None
    for integration in profile.integrations:
        if integration.name == "clickup" and integration.activated:
            return integration
    return None


class GetWorkspacesUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str) -> List[Dict]:
        context = self.context_factory()
        profile = await context.repositories.profile.find_by_user_id(user_id)

        integration = _find_clickup_integration(profile)
        if not integration:
            raise NewApplicationError(ClickUpIntegrationNotFoundError)

        api_token = integration.config.get("api_token", "")
        if not api_token:
            raise NewApplicationError(ClickUpIntegrationConfigError)

        try:
            client = context.integrations.make_clickup_client(api_token)
            teams = await asyncio.to_thread(client.get_teams)
            return teams
        except Exception as e:
            logger.error(f"Error fetching ClickUp workspaces: {e}", exc_info=True)
            raise NewApplicationError(ClickUpWorkspaceQueryError, e)
