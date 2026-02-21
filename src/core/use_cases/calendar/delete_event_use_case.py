import logging
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarEventDeleteError

logger = logging.getLogger(__name__)


class DeleteEventUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str, event_id: str, **kwargs) -> None:
        try:
            self.context_factory.integrations.google_calendar.delete_event(
                user_id=user_id, event_id=event_id
            )
        except Exception as e:
            logger.error(f"Error deleting calendar event: {e}", exc_info=True)
            raise NewApplicationError(CalendarEventDeleteError, e)
