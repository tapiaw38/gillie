from datetime import datetime
from pymongo.errors import PyMongoError
from src.core.domain.calendar import CalendarEvent
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarEventUpdateError


def update_event(client, event: CalendarEvent) -> None:
    try:
        doc = event.dict(by_alias=True, exclude_none=True)
        doc["updated_at"] = datetime.now()
        client.replace_one({"_id": event.id, "user_id": event.user_id}, doc)
    except PyMongoError as e:
        raise NewApplicationError(CalendarEventUpdateError, e)
