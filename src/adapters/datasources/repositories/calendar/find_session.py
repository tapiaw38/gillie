from pymongo.errors import PyMongoError
from typing import Optional
from src.core.domain.calendar import CalendarSession
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarSessionQueryError


def find_active_session(client, user_id: str) -> Optional[CalendarSession]:
    try:
        doc = client.find_one({"user_id": user_id, "is_active": True})
        if doc:
            doc["_id"] = str(doc["_id"])
            return CalendarSession(**doc)
        return None
    except PyMongoError as e:
        raise NewApplicationError(CalendarSessionQueryError, e)
