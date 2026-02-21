import logging
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarOAuthError

logger = logging.getLogger(__name__)


class GetAuthorizationUrlUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str) -> str:
        try:
            auth_url = self.context_factory.integrations.google_calendar.get_authorization_url(user_id)
            if not auth_url:
                raise NewApplicationError(CalendarOAuthError)
            return auth_url
        except Exception as e:
            logger.error(f"Error getting authorization URL: {e}", exc_info=True)
            raise NewApplicationError(CalendarOAuthError, e)
