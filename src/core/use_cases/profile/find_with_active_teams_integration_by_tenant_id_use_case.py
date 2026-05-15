from typing import Optional

from src.core.platform.appcontext.appcontext import Factory
from src.core.domain import Profile


class FindWithActiveTeamsIntegrationByTenantIdUseCase:
    """Find the profile whose active Teams integration matches the given tenant ID."""

    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, tenant_id: str) -> Optional[Profile]:
        if not tenant_id:
            return None

        context = self.context_factory()
        profiles = await context.repositories.profile.find_all()
        for profile in profiles:
            for integration in profile.integrations or []:
                if (
                    integration.name == "teams"
                    and integration.activated
                    and integration.config.get("tenant_id") == tenant_id
                ):
                    return profile
        return None
