import asyncio
import logging
from typing import Dict, List, Optional

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.clickup import (
    ClickUpIntegrationNotFoundError,
    ClickUpIntegrationConfigError,
    ClickUpTaskCreateError,
    ClickUpTaskNameRequiredError,
    ClickUpListIdRequiredError,
)

logger = logging.getLogger(__name__)


def _find_clickup_integration(profile):
    if not profile or not profile.integrations:
        return None
    for integration in profile.integrations:
        if integration.name == "clickup" and integration.activated:
            return integration
    return None


class CreateTaskUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(
        self,
        user_id: str,
        list_id: str,
        name: str,
        *,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        due_date: Optional[int] = None,
        assignees: Optional[List[int]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict:
        if not name or not name.strip():
            raise NewApplicationError(ClickUpTaskNameRequiredError)
        if not list_id or not list_id.strip():
            raise NewApplicationError(ClickUpListIdRequiredError)

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
            task = await asyncio.to_thread(
                client.create_task,
                list_id,
                name,
                description=description,
                status=status,
                priority=priority,
                due_date=due_date,
                assignees=assignees,
                tags=tags,
            )
            return task
        except Exception as e:
            logger.error(f"Error creating ClickUp task: {e}", exc_info=True)
            raise NewApplicationError(ClickUpTaskCreateError, e)
