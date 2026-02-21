from pymongo.errors import PyMongoError
from typing import Optional, List
from datetime import datetime
from src.core.domain.calendar import CalendarEvent
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarEventQueryError


def find_events_by_user(
    client,
    user_id: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 50,
) -> List[CalendarEvent]:
    try:
        query: dict = {"user_id": user_id, "status": {"$ne": "cancelled"}}
        if start:
            query["start_time"] = {"$gte": start}
        if end:
            query.setdefault("start_time", {})["$lte"] = end
        docs = client.find(query).sort("start_time", 1).limit(limit)
        return [CalendarEvent(**doc) for doc in docs]
    except PyMongoError as e:
        raise NewApplicationError(CalendarEventQueryError, e)
