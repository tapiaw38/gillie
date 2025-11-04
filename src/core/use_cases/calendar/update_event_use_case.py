from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import CommonInternalServerError
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class UpdateEventUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(
        self,
        event_id: str,
        user_id: str,
        profile_id: str,
        title: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        jwt_token: Optional[str] = None
    ) -> Dict:
        """
        Update an existing calendar event.

        Args:
            event_id: ID of the event to update
            user_id: User ID from auth system
            profile_id: Profile ID for this integration
            title: Event title
            start_time: Event start time (ISO format)
            end_time: Event end time (ISO format)
            description: Event description (optional)
            location: Event location (optional)
            jwt_token: JWT token for authentication (optional)

        Returns:
            Updated event data

        Raises:
            ApplicationError: If failed to update event
        """
        try:
            updated_event = self.context_factory.integrations.google_calendar.update_event(
                event_id=event_id,
                user_id=user_id,
                profile_id=profile_id,
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location,
                jwt_token=jwt_token
            )

            if not updated_event:
                raise NewApplicationError(CommonInternalServerError)

            return updated_event

        except Exception as e:
            logger.error(f"Error updating calendar event: {str(e)}", exc_info=True)
            raise NewApplicationError(CommonInternalServerError, e)
