import logging
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.drive import DriveOAuthError

logger = logging.getLogger(__name__)


class GetAuthorizationUrlUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(self, user_id: str) -> str:
        try:
            context = self.context_factory()
            url = context.integrations.google_drive.get_authorization_url(user_id)
            if not url:
                raise NewApplicationError(DriveOAuthError)
            return url
        except Exception as e:
            logger.error(f"Error getting Drive auth URL: {e}", exc_info=True)
            raise NewApplicationError(DriveOAuthError, e)
