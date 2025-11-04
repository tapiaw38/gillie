from src.core.platform.appcontext.appcontext import Factory
import logging

logger = logging.getLogger(__name__)


class CheckSessionStatusUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str, profile_id: str) -> bool:
        """
        Check if user has an active Google Calendar session.

        Args:
            user_id: User ID from auth system
            profile_id: Profile ID for this integration

        Returns:
            True if session is active, False otherwise
        """
        try:
            is_active = self.context_factory.integrations.google_calendar.check_session_status(
                user_id, profile_id
            )
            return is_active

        except Exception as e:
            logger.error(f"Error checking session status: {str(e)}", exc_info=True)
            return False
