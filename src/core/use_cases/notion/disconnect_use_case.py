import logging

from src.core.platform.appcontext.appcontext import Factory

from ._helpers import get_notion_integration, get_notion_profile, save_notion_config

logger = logging.getLogger(__name__)


class DisconnectUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str) -> None:
        context = self.context_factory()
        profile = await get_notion_profile(context, user_id)
        integration = get_notion_integration(profile)
        if not integration:
            return

        try:
            await context.integrations.notion.revoke_token(integration.config)
        except Exception:
            logger.warning("Could not revoke Notion token for user_id=%s", user_id, exc_info=True)

        await save_notion_config(
            context,
            user_id,
            {"profile_id": user_id, "is_connected": False},
            activated=False,
        )
