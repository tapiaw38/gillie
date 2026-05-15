import asyncio
import logging
from typing import Dict

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.clickup import (
    ClickUpIntegrationNotFoundError,
    ClickUpIntegrationConfigError,
    ClickUpCommentCreateError,
)

logger = logging.getLogger(__name__)


def _find_clickup_integration(profile):
    if not profile or not profile.integrations:
        return None
    for integration in profile.integrations:
        if integration.name == "clickup" and integration.activated:
            return integration
    return None


class AddCommentUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, task_id: str, comment_text: str) -> Dict:
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
            result = await asyncio.to_thread(client.add_task_comment, task_id, comment_text)
            return result
        except Exception as e:
            logger.error(f"Error adding comment to ClickUp task {task_id}: {e}", exc_info=True)
            raise NewApplicationError(ClickUpCommentCreateError, e)
