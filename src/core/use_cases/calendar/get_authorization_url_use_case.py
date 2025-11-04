from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import CommonInternalServerError
import logging

logger = logging.getLogger(__name__)


class GetAuthorizationUrlUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str, profile_id: str) -> str:
        """
        Get Google Calendar OAuth authorization URL.

        Args:
            user_id: User ID from auth system
            profile_id: Profile ID for this integration

        Returns:
            Authorization URL

        Raises:
            ApplicationError: If failed to get authorization URL
        """
        try:
            auth_url = self.context_factory.integrations.google_calendar.get_authorization_url(
                user_id, profile_id
            )

            if not auth_url:
                raise NewApplicationError(CommonInternalServerError)

            return auth_url

        except Exception as e:
            logger.error(f"Error getting authorization URL: {str(e)}", exc_info=True)
            raise NewApplicationError(CommonInternalServerError, e)
