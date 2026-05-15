import asyncio
from typing import Dict

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import ValidationError


class VerifySlackConnectionUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str) -> Dict:
        context = self.context_factory()
        profile = await context.repositories.profile.find_by_user_id(user_id)

        if not profile or not profile.integrations:
            raise NewApplicationError(ValidationError, Exception("Slack integration is not configured"))

        slack_integration = None
        for integration in profile.integrations:
            if integration.name == "slack" and integration.activated:
                slack_integration = integration
                break

        if not slack_integration:
            raise NewApplicationError(ValidationError, Exception("Slack integration is not activated"))

        bot_token = slack_integration.config.get("bot_token", "")
        signing_secret = slack_integration.config.get("signing_secret", "")
        if not bot_token or not signing_secret:
            raise NewApplicationError(
                ValidationError,
                Exception("Slack configuration is incomplete: bot_token and signing_secret are required"),
            )

        client = context.integrations.make_slack_client(
            bot_token=bot_token,
            signing_secret=signing_secret,
        )

        return await asyncio.to_thread(client.auth_test)
