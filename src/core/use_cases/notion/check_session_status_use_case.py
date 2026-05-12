from src.core.platform.appcontext.appcontext import Factory

from ._helpers import get_notion_integration, get_notion_profile, save_notion_config


class CheckSessionStatusUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str) -> dict:
        context = self.context_factory()
        profile = await get_notion_profile(context, user_id)
        integration = get_notion_integration(profile)
        if not integration or not integration.config.get("access_token"):
            return {"is_active": False, "user_id": user_id}

        is_active, _payload, updated_config = await context.integrations.notion.check_session_status(
            integration.config
        )
        current_config = integration.config
        if updated_config:
            await save_notion_config(context, user_id, updated_config, activated=integration.activated)
            current_config = updated_config

        return {
            "is_active": is_active,
            "user_id": user_id,
            "workspace_name": current_config.get("workspace_name"),
            "workspace_icon": current_config.get("workspace_icon"),
            "owner_name": (current_config.get("owner") or {}).get("name"),
        }
