import logging
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarSyncError

logger = logging.getLogger(__name__)


class SyncEventsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str) -> dict:
        try:
            return self.context_factory.integrations.google_calendar.sync_events(user_id)
        except Exception as e:
            logger.error(f"Error syncing calendar events: {e}", exc_info=True)
            raise NewApplicationError(CalendarSyncError, e)
