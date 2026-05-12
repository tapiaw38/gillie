from src.core.platform.appcontext.appcontext import Factory

from ._helpers import save_notion_config


class HandleOAuthCallbackUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, code: str) -> dict:
        context = self.context_factory()
        payload = await context.integrations.notion.handle_oauth_callback(code)
        owner_user = (payload.get("owner") or {}).get("user") or {}
        config = {
            "access_token": payload.get("access_token", ""),
            "refresh_token": payload.get("refresh_token", ""),
            "workspace_id": payload.get("workspace_id", ""),
            "workspace_name": payload.get("workspace_name", ""),
            "workspace_icon": payload.get("workspace_icon", ""),
            "bot_id": payload.get("bot_id", ""),
            "owner": owner_user,
            "is_connected": True,
            "profile_id": user_id,
        }
        await save_notion_config(context, user_id, config, activated=True)
        return config
