import logging
from typing import Optional, List, Dict
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarEventQueryError

logger = logging.getLogger(__name__)


class ListEventsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        **kwargs,
    ) -> List[Dict]:
        try:
            context = self.context_factory()
            return await context.integrations.google_calendar.list_events(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Error listing calendar events: {e}", exc_info=True)
            raise NewApplicationError(CalendarEventQueryError, e)
