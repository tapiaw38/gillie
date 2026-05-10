import logging

from src.core.platform.appcontext.appcontext import Factory

logger = logging.getLogger(__name__)

INTEGRATION_NAME = "google_drive"


class CheckSessionStatusUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str) -> bool:
        try:
            context = self.context_factory()
            profile = await context.repositories.profile.find_by_user_id(user_id)
            if not profile:
                return False
            drive_integration = next(
                (i for i in (profile.integrations or []) if i.name == INTEGRATION_NAME),
                None,
            )
            if drive_integration is None:
                return False
            config = drive_integration.config or {}
            return bool(config.get("access_token"))
        except Exception as e:
            logger.error(f"Error checking Drive session: {e}", exc_info=True)
            return False
