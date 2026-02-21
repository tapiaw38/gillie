from datetime import datetime
from pymongo.errors import PyMongoError
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.calendar import CalendarEventDeleteError


def delete_event(client, event_id: str, user_id: str) -> None:
    try:
        client.update_one(
            {"_id": event_id, "user_id": user_id},
            {"$set": {"status": "cancelled", "updated_at": datetime.now()}},
        )
    except PyMongoError as e:
        raise NewApplicationError(CalendarEventDeleteError, e)
