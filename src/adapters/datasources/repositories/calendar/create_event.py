from pymongo.errors import PyMongoError
from src.core.domain.calendar import CalendarEvent
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarEventCreateError


def create_event(client, event: CalendarEvent) -> str:
    try:
        doc = event.dict(by_alias=True, exclude_none=True)
        result = client.insert_one(doc)
        return str(result.inserted_id)
    except PyMongoError as e:
        raise NewApplicationError(CalendarEventCreateError, e)
