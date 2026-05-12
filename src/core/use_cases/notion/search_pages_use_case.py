from src.core.platform.appcontext.appcontext import Factory

from ._helpers import get_notion_integration, get_notion_profile, save_notion_config


class SearchPagesUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(
        self,
        user_id: str,
        query: str = "",
        page_size: int = 20,
        start_cursor: str | None = None,
    ) -> dict:
        context = self.context_factory()
        profile = await get_notion_profile(context, user_id)
        integration = get_notion_integration(profile)
        if not integration:
            return {"results": [], "next_cursor": None, "has_more": False}

        payload, updated_config = await context.integrations.notion.search_pages(
            integration.config,
            query=query,
            page_size=page_size,
            start_cursor=start_cursor,
        )
        if updated_config:
            await save_notion_config(context, user_id, updated_config, activated=integration.activated)

        return payload
