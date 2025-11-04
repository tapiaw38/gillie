from src.core.platform.appcontext.appcontext import Factory
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class ListEventsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(
        self,
        user_id: str,
        profile_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        jwt_token: Optional[str] = None
    ) -> List[Dict]:
        """
        List calendar events for the user.

        Args:
            user_id: User ID from auth system
            profile_id: Profile ID for this integration
            start_date: Filter events from this date (ISO format, optional)
            end_date: Filter events until this date (ISO format, optional)
            limit: Maximum number of events to return (default: 50)
            jwt_token: JWT token for authentication (optional)

        Returns:
            List of event data dictionaries
        """
        try:
            events = self.context_factory.integrations.google_calendar.list_events(
                user_id=user_id,
                profile_id=profile_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                jwt_token=jwt_token
            )

            return events if events else []

        except Exception as e:
            logger.error(f"Error listing calendar events: {str(e)}", exc_info=True)
            return []
