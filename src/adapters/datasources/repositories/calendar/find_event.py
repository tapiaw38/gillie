from pymongo.errors import PyMongoError
from typing import Optional
from src.core.domain.calendar import CalendarEvent
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarEventQueryError


def find_event_by_id(client, event_id: str, user_id: str) -> Optional[CalendarEvent]:
    try:
        doc = client.find_one({"_id": event_id, "user_id": user_id})
        if doc:
            return CalendarEvent(**doc)
        return None
    except PyMongoError as e:
        raise NewApplicationError(CalendarEventQueryError, e)


def find_event_by_google_id(client, google_id: str, user_id: str) -> Optional[CalendarEvent]:
    try:
        doc = client.find_one({"google_id": google_id, "user_id": user_id})
        if doc:
            return CalendarEvent(**doc)
        return None
    except PyMongoError as e:
        raise NewApplicationError(CalendarEventQueryError, e)
