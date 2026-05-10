import logging
from typing import Optional, Dict
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarEventUpdateError

logger = logging.getLogger(__name__)


class UpdateEventUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str, event_id: str, **fields) -> Dict:
        try:
            context = self.context_factory()
            return await context.integrations.google_calendar.update_event(
                user_id=user_id, event_id=event_id, **fields
            )
        except Exception as e:
            logger.error(f"Error updating calendar event: {e}", exc_info=True)
            raise NewApplicationError(CalendarEventUpdateError, e)
