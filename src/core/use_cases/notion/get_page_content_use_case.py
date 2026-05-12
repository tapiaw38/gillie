from src.core.platform.appcontext.appcontext import Factory

from ._helpers import get_notion_integration, get_notion_profile, save_notion_config


class GetPageContentUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, page_id: str, max_depth: int = 4) -> dict:
        context = self.context_factory()
        profile = await get_notion_profile(context, user_id)
        integration = get_notion_integration(profile)
        if not integration:
            raise RuntimeError("Notion integration is not configured")

        payload, updated_config = await context.integrations.notion.get_page_content(
            integration.config,
            page_id,
            max_depth=max_depth,
        )
        if updated_config:
            await save_notion_config(context, user_id, updated_config, activated=integration.activated)
        return payload
