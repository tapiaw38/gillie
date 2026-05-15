from typing import Optional
from src.core.platform.appcontext.appcontext import Factory
from src.core.domain import Profile


class FindWithActiveTeamsIntegrationUseCase:
    """Find the first profile with an active Teams integration."""

    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self) -> Optional[Profile]:
        context = self.context_factory()
        profiles = await context.repositories.profile.find_all()
        for profile in profiles:
            if profile.integrations:
                for integration in profile.integrations:
                    if integration.name == "teams" and integration.activated:
                        return profile
        return None
