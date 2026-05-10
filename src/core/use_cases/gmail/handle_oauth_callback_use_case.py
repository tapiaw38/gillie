import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.gmail import GmailOAuthError

logger = logging.getLogger(__name__)


class HandleOAuthCallbackUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, code: str) -> dict:
        try:
            context = self.context_factory()
            return await context.integrations.gmail.handle_oauth_callback(user_id, code)
        except Exception as e:
            logger.error(f"Error handling Gmail OAuth callback: {e}", exc_info=True)
            raise NewApplicationError(GmailOAuthError, e)
