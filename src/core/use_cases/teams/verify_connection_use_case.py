import asyncio
import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.teams import (
    TeamsIntegrationNotFoundError,
    TeamsIntegrationConfigError,
    TeamsVerifyError,
)

logger = logging.getLogger(__name__)


class VerifyTeamsConnectionUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str) -> bool:
        context = self.context_factory()
        profile = await context.repositories.profile.find_by_user_id(user_id)

        integration = None
        if profile and profile.integrations:
            for integ in profile.integrations:
                if integ.name == "teams" and integ.activated:
                    integration = integ
                    break

        if not integration:
            raise NewApplicationError(TeamsIntegrationNotFoundError)

        app_id = integration.config.get("app_id", "")
        app_password = integration.config.get("app_password", "")
        if not app_id or not app_password:
            raise NewApplicationError(TeamsIntegrationConfigError)

        try:
            client = context.integrations.make_teams_client(app_id, app_password)
            result = await asyncio.to_thread(client.verify_credentials)
            return result
        except Exception as e:
            logger.error(f"Teams verify connection error: {e}", exc_info=True)
            raise NewApplicationError(TeamsVerifyError, e)
