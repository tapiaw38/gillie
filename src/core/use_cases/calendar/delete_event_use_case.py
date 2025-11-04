from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import CommonInternalServerError
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DeleteEventUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(
        self,
        event_id: str,
        user_id: str,
        profile_id: str,
        jwt_token: Optional[str] = None
    ) -> bool:
        """
        Delete a calendar event.

        Args:
            event_id: ID of the event to delete
            user_id: User ID from auth system
            profile_id: Profile ID for this integration
            jwt_token: JWT token for authentication (optional)

        Returns:
            True if deletion was successful

        Raises:
            ApplicationError: If failed to delete event
        """
        try:
            success = self.context_factory.integrations.google_calendar.delete_event(
                event_id=event_id,
                user_id=user_id,
                profile_id=profile_id,
                jwt_token=jwt_token
            )

            if not success:
                raise NewApplicationError(CommonInternalServerError)

            return success

        except Exception as e:
            logger.error(f"Error deleting calendar event: {str(e)}", exc_info=True)
            raise NewApplicationError(CommonInternalServerError, e)
