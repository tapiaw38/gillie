import logging
from typing import Optional, List, Dict
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarEventCreateError

logger = logging.getLogger(__name__)


class CreateEventUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    def execute(
        self,
        user_id: str,
        title: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[Dict]] = None,
        reminders: Optional[List[Dict]] = None,
        time_zone: Optional[str] = None,
        **kwargs,
    ) -> Dict:
        try:
            context = self.context_factory()
            return context.integrations.google_calendar.create_event(
                user_id=user_id,
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location,
                attendees=attendees,
                reminders=reminders,
                time_zone=time_zone,
            )
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}", exc_info=True)
            raise NewApplicationError(CalendarEventCreateError, e)
