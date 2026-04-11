import logging

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.gmail import GmailOAuthError

logger = logging.getLogger(__name__)


class GetAuthorizationUrlUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, user_id: str) -> str:
        try:
            context = self.context_factory()
            auth_url = context.integrations.gmail.get_authorization_url(user_id)
            if not auth_url:
                raise NewApplicationError(GmailOAuthError)
            return auth_url
        except Exception as e:
            logger.error(f"Error getting Gmail authorization URL: {e}", exc_info=True)
            raise NewApplicationError(GmailOAuthError, e)
