from src.core.domain.notion import NotionCredentials
from src.core.platform.appcontext.appcontext import Factory


class SetCredentialsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        context = self.context_factory()
        await context.repositories.notion.save_credentials(
            NotionCredentials(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
            )
        )
