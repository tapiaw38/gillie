from typing import Optional

from src.core.platform.appcontext.appcontext import Factory
from src.core.domain import Profile


class FindWithActiveSlackIntegrationByTeamIdUseCase:
    """
    Find the profile whose active Slack integration matches the given workspace team ID.
    """

    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, team_id: str) -> Optional[Profile]:
        if not team_id:
            return None

        context = self.context_factory()
        profiles = await context.repositories.profile.find_all()

        for profile in profiles:
            if not profile.integrations:
                continue
            for integration in profile.integrations:
                if (
                    integration.name == "slack"
                    and integration.activated
                    and integration.config.get("team_id") == team_id
                ):
                    return profile

        return None
