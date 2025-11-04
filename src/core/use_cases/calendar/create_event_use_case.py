from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import CommonInternalServerError
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class CreateEventUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(
        self,
        user_id: str,
        profile_id: str,
        title: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[Dict[str, str]]] = None,
        reminders: Optional[List[Dict[str, any]]] = None,
        jwt_token: Optional[str] = None
    ) -> Dict:
        """
        Create a new calendar event.

        Args:
            user_id: User ID from auth system
            profile_id: Profile ID for this integration
            title: Event title
            start_time: Event start time (ISO format)
            end_time: Event end time (ISO format)
            description: Event description (optional)
            location: Event location (optional)
            attendees: List of attendees with email and name (optional)
            reminders: List of reminder configurations (optional)
            jwt_token: JWT token for authentication (optional)

        Returns:
            Created event data

        Raises:
            ApplicationError: If failed to create event
        """
        try:
            created_event = self.context_factory.integrations.google_calendar.create_event(
                user_id=user_id,
                profile_id=profile_id,
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location,
                attendees=attendees,
                reminders=reminders,
                jwt_token=jwt_token
            )

            if not created_event:
                raise NewApplicationError(CommonInternalServerError)

            return created_event

        except Exception as e:
            logger.error(f"Error creating calendar event: {str(e)}", exc_info=True)
            raise NewApplicationError(CommonInternalServerError, e)
