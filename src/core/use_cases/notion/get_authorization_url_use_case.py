from src.core.platform.appcontext.appcontext import Factory


class GetAuthorizationUrlUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str) -> str:
        context = self.context_factory()
        return await context.integrations.notion.get_authorization_url(user_id)
